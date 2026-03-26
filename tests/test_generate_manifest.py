"""Comprehensive tests for scripts/generate_manifest.py."""

import json
import os
import sys

import pytest

# Ensure the scripts package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "scripts"))

import generate_manifest as gm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path, obj):
    """Write a Python object as JSON to *path*, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f)


def _patch_repo(monkeypatch, tmp_path):
    """Point the module's REPO_ROOT at *tmp_path*."""
    monkeypatch.setattr(gm, "REPO_ROOT", str(tmp_path))


# ---------------------------------------------------------------------------
# A. _load_json
# ---------------------------------------------------------------------------

class TestLoadJson:
    def test_missing_file_returns_none(self, tmp_path):
        assert gm._load_json(str(tmp_path / "nope.json")) is None

    def test_invalid_json_returns_none(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json!!")
        assert gm._load_json(str(bad)) is None

    def test_valid_json_returns_dict(self, tmp_path):
        good = tmp_path / "good.json"
        good.write_text('{"key": "value"}')
        assert gm._load_json(str(good)) == {"key": "value"}


# ---------------------------------------------------------------------------
# B. _sorted_subdirs
# ---------------------------------------------------------------------------

class TestSortedSubdirs:
    def test_returns_sorted_dir_names(self, tmp_path):
        (tmp_path / "charlie").mkdir()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "bravo").mkdir()
        assert gm._sorted_subdirs(str(tmp_path)) == ["alpha", "bravo", "charlie"]

    def test_skips_files(self, tmp_path):
        (tmp_path / "adir").mkdir()
        (tmp_path / "afile.txt").write_text("hi")
        assert gm._sorted_subdirs(str(tmp_path)) == ["adir"]

    def test_nonexistent_returns_empty(self, tmp_path):
        assert gm._sorted_subdirs(str(tmp_path / "nope")) == []


# ---------------------------------------------------------------------------
# C. _extract_model_scores
# ---------------------------------------------------------------------------

class TestExtractModelScores:
    def test_extracts_scores(self):
        bundle = {
            "model_adapters": {
                "modelA": {"score": 0.9},
                "modelB": {"score": 0.7, "extra": "ignored"},
            }
        }
        assert gm._extract_model_scores(bundle) == {"modelA": 0.9, "modelB": 0.7}

    def test_skips_entries_without_score(self):
        bundle = {
            "model_adapters": {
                "modelA": {"score": 0.5},
                "modelB": {"other": "stuff"},
            }
        }
        assert gm._extract_model_scores(bundle) == {"modelA": 0.5}

    def test_empty_model_adapters(self):
        assert gm._extract_model_scores({"model_adapters": {}}) == {}

    def test_missing_model_adapters_key(self):
        assert gm._extract_model_scores({}) == {}


# ---------------------------------------------------------------------------
# D. _build_nerve_entry
# ---------------------------------------------------------------------------

class TestBuildNerveEntry:
    def test_correct_fields(self):
        bundle = {
            "description": "A nerve",
            "role": "code",
            "tags": ["tag1"],
            "authors": [{"github": "user1"}],
            "version": "2.0",
            "tools": [{"name": "t1"}, {"name": "t2"}],
            "model_adapters": {"m1": {"score": 0.8}},
        }
        entry = gm._build_nerve_entry(bundle)
        assert entry == {
            "description": "A nerve",
            "role": "code",
            "tags": ["tag1"],
            "authors": [{"github": "user1"}],
            "version": "2.0",
            "tools": ["t1", "t2"],
            "model_scores": {"m1": 0.8},
        }

    def test_defaults_for_missing_keys(self):
        entry = gm._build_nerve_entry({})
        assert entry == {
            "description": "",
            "role": "tool",
            "tags": [],
            "authors": [],
            "version": "1.0",
            "tools": [],
            "model_scores": {},
        }


# ---------------------------------------------------------------------------
# E. collect_nerves
# ---------------------------------------------------------------------------

class TestCollectNerves:
    def test_empty_nerves_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "nerves").mkdir()
        assert gm.collect_nerves() == {}

    def test_missing_nerves_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        # nerves/ does not exist at all
        assert gm.collect_nerves() == {}

    def test_valid_nerve(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        nerve_dir = tmp_path / "nerves" / "my_nerve"
        nerve_dir.mkdir(parents=True)
        bundle = {
            "description": "desc",
            "role": "tool",
            "tags": ["x"],
            "authors": [{"github": "gh"}],
            "version": "1.0",
            "tools": [{"name": "do_thing"}],
            "model_adapters": {},
        }
        _write_json(str(nerve_dir / "bundle.json"), bundle)
        result = gm.collect_nerves()
        assert "my_nerve" in result
        assert result["my_nerve"]["description"] == "desc"
        assert result["my_nerve"]["tools"] == ["do_thing"]

    def test_skips_nerve_without_bundle(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "nerves" / "bad_nerve").mkdir(parents=True)
        assert gm.collect_nerves() == {}


# ---------------------------------------------------------------------------
# F. _read_qualification_score
# ---------------------------------------------------------------------------

class TestReadQualificationScore:
    def test_reads_score(self, tmp_path):
        _write_json(str(tmp_path / "qualification.json"), {"overall_score": 0.85})
        assert gm._read_qualification_score(str(tmp_path)) == 0.85

    def test_missing_file_returns_none(self, tmp_path):
        assert gm._read_qualification_score(str(tmp_path)) is None

    def test_missing_overall_score_key(self, tmp_path):
        _write_json(str(tmp_path / "qualification.json"), {"other": 1})
        assert gm._read_qualification_score(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# G. _build_adapter_entry
# ---------------------------------------------------------------------------

class TestBuildAdapterEntry:
    def test_with_model_name(self):
        meta = {
            "model": "llama3.2-3b",
            "size_class": "small",
            "provider": "ollama",
            "contributor": {"github": "user1"},
        }
        entry = gm._build_adapter_entry(meta, "tool", "small", "llama3.2-3b", 0.9)
        assert entry == {
            "role": "tool",
            "model": "llama3.2-3b",
            "size_class": "small",
            "provider": "ollama",
            "score": 0.9,
            "contributor": "user1",
        }

    def test_without_model_name_falls_back_to_size_class(self):
        meta = {"contributor": {"github": "u"}}
        entry = gm._build_adapter_entry(meta, "code", "medium", None, None)
        # model falls back: meta has no "model", model_name is None -> size_class
        assert entry["model"] == "medium"
        assert entry["score"] is None

    def test_model_name_used_when_meta_has_no_model(self):
        meta = {"contributor": {"github": "u"}}
        entry = gm._build_adapter_entry(meta, "tool", "small", "phi3", 0.5)
        assert entry["model"] == "phi3"

    def test_score_none_preserved(self):
        meta = {}
        entry = gm._build_adapter_entry(meta, "tool", "small", None, None)
        assert entry["score"] is None

    def test_defaults_for_missing_meta_keys(self):
        entry = gm._build_adapter_entry({}, "tool", "small", None, None)
        assert entry["provider"] == ""
        assert entry["contributor"] == ""


# ---------------------------------------------------------------------------
# H. collect_adapters
# ---------------------------------------------------------------------------

class TestCollectAdapters:
    def test_empty_adapters_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "adapters").mkdir()
        assert gm.collect_adapters() == {}

    def test_missing_adapters_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        assert gm.collect_adapters() == {}

    def test_valid_size_class_default_adapter(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        ad = tmp_path / "adapters" / "tool" / "small"
        ad.mkdir(parents=True)
        _write_json(str(ad / "meta.json"), {
            "model": "tinylm",
            "size_class": "small",
            "contributor": {"github": "alice"},
        })
        result = gm.collect_adapters()
        assert "tool/small" in result
        assert result["tool/small"]["model"] == "tinylm"

    def test_valid_model_specific_adapter(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        ad = tmp_path / "adapters" / "code" / "medium" / "phi3"
        ad.mkdir(parents=True)
        _write_json(str(ad / "meta.json"), {
            "model": "phi3",
            "size_class": "medium",
            "provider": "ollama",
            "contributor": {"github": "bob"},
        })
        _write_json(str(ad / "qualification.json"), {"overall_score": 0.92})
        result = gm.collect_adapters()
        assert "code/medium/phi3" in result
        assert result["code/medium/phi3"]["score"] == 0.92

    def test_skips_adapter_without_meta(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "adapters" / "tool" / "small").mkdir(parents=True)
        # no meta.json
        assert gm.collect_adapters() == {}


# ---------------------------------------------------------------------------
# I. collect_tools
# ---------------------------------------------------------------------------

class TestCollectTools:
    def test_valid_tool(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        td = tmp_path / "tools" / "web_search"
        td.mkdir(parents=True)
        _write_json(str(td / "meta.json"), {
            "name": "web_search",
            "version": "1.0.0",
            "description": "Searches the web for info",
            "implementations": {"python": "tool.py"},
            "author": {"github": "dev1"},
            "category": "search",
            "tags": ["search", "web"],
            "parameters": [{"name": "query", "type": "string", "description": "query"}],
            "requires_api_key": True,
        })
        result = gm.collect_tools()
        assert "web_search" in result
        t = result["web_search"]
        assert t["name"] == "web_search"
        assert t["version"] == "1.0.0"
        assert t["implementations"] == {"python": "tool.py"}
        assert t["author"] == "dev1"
        assert t["requires_api_key"] is True
        assert t["tags"] == ["search", "web"]

    def test_missing_meta_skipped(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "tools" / "broken_tool").mkdir(parents=True)
        assert gm.collect_tools() == {}

    def test_empty_tools_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "tools").mkdir()
        assert gm.collect_tools() == {}

    def test_missing_tools_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        assert gm.collect_tools() == {}

    def test_tool_defaults(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        td = tmp_path / "tools" / "minimal"
        td.mkdir(parents=True)
        _write_json(str(td / "meta.json"), {})
        result = gm.collect_tools()
        t = result["minimal"]
        assert t["name"] == "minimal"
        assert t["version"] == ""
        assert t["description"] == ""
        assert t["implementations"] == {}
        assert t["author"] == ""
        assert t["category"] == ""
        assert t["tags"] == []
        assert t["parameters"] == []
        assert t["requires_api_key"] is False


# ---------------------------------------------------------------------------
# J. collect_mcps
# ---------------------------------------------------------------------------

class TestCollectMcps:
    def test_valid_mcp_with_auth_fields(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        md = tmp_path / "mcps" / "brave_search"
        md.mkdir(parents=True)
        _write_json(str(md / "meta.json"), {
            "name": "brave_search",
            "version": "0.1.0",
            "description": "Brave search engine MCP",
            "source": "npm",
            "package": "@anthropic/brave-search",
            "command": ["npx", "-y", "@anthropic/brave-search"],
            "auth_type": "api_key",
            "auth_env": "BRAVE_API_KEY",
            "tools": ["brave_web_search"],
            "capabilities": ["search", "web"],
            "category": "search",
        })
        result = gm.collect_mcps()
        assert "brave_search" in result
        m = result["brave_search"]
        assert m["auth_type"] == "api_key"
        assert m["auth_env"] == "BRAVE_API_KEY"
        assert m["command"] == ["npx", "-y", "@anthropic/brave-search"]

    def test_mcp_without_auth_env(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        md = tmp_path / "mcps" / "basic"
        md.mkdir(parents=True)
        _write_json(str(md / "meta.json"), {
            "name": "basic",
            "version": "1.0.0",
            "description": "A basic MCP server",
            "source": "npm",
            "package": "basic-mcp",
            "command": ["npx", "basic-mcp"],
            "auth_type": "none",
            "tools": ["do_thing"],
            "capabilities": ["misc"],
            "category": "utilities",
        })
        result = gm.collect_mcps()
        assert "auth_env" not in result["basic"]
        assert "auth_provider" not in result["basic"]

    def test_mcp_with_auth_provider(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        md = tmp_path / "mcps" / "oauth_mcp"
        md.mkdir(parents=True)
        _write_json(str(md / "meta.json"), {
            "name": "oauth_mcp",
            "version": "1.0.0",
            "description": "An OAuth MCP server",
            "source": "github",
            "package": "https://github.com/example/oauth-mcp",
            "command": ["node", "server.js"],
            "auth_type": "oauth2",
            "auth_provider": "google",
            "tools": [],
            "capabilities": ["auth"],
            "category": "auth",
        })
        result = gm.collect_mcps()
        assert result["oauth_mcp"]["auth_provider"] == "google"

    def test_missing_meta_skipped(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "mcps" / "broken").mkdir(parents=True)
        assert gm.collect_mcps() == {}

    def test_empty_mcps_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "mcps").mkdir()
        assert gm.collect_mcps() == {}

    def test_missing_mcps_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        assert gm.collect_mcps() == {}


# ---------------------------------------------------------------------------
# K. collect_connectors
# ---------------------------------------------------------------------------

class TestCollectConnectors:
    def test_valid_connector(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        cd = tmp_path / "connectors" / "discord"
        cd.mkdir(parents=True)
        _write_json(str(cd / "meta.json"), {
            "name": "discord",
            "version": "1.0.0",
            "description": "Discord connector for Arqitect",
            "language": "javascript",
            "platforms": ["discord"],
            "author": {"github": "dev1"},
            "capabilities": {"incoming": ["message"], "outgoing": ["reply"]},
            "config_fields": [{"name": "token", "required": True}],
        })
        result = gm.collect_connectors()
        assert "discord" in result
        c = result["discord"]
        assert c["name"] == "discord"
        assert c["language"] == "javascript"
        assert c["platforms"] == ["discord"]
        assert c["author"] == "dev1"
        assert c["capabilities"] == {"incoming": ["message"], "outgoing": ["reply"]}
        assert c["config_fields"] == [{"name": "token", "required": True}]

    def test_missing_meta_skipped(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "connectors" / "broken").mkdir(parents=True)
        assert gm.collect_connectors() == {}

    def test_empty_connectors_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        (tmp_path / "connectors").mkdir()
        assert gm.collect_connectors() == {}

    def test_missing_connectors_dir(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        assert gm.collect_connectors() == {}

    def test_connector_defaults(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)
        cd = tmp_path / "connectors" / "minimal"
        cd.mkdir(parents=True)
        _write_json(str(cd / "meta.json"), {})
        result = gm.collect_connectors()
        c = result["minimal"]
        assert c["name"] == "minimal"
        assert c["version"] == ""
        assert c["description"] == ""
        assert c["language"] == ""
        assert c["platforms"] == []
        assert c["author"] == ""
        assert c["capabilities"] == {}
        assert c["config_fields"] == []


# ---------------------------------------------------------------------------
# L. build_leaderboard
# ---------------------------------------------------------------------------

class TestBuildLeaderboard:
    def test_groups_by_size_class_sorted_desc(self):
        adapters = {
            "a": {"model": "m1", "score": 0.5, "size_class": "small", "contributor": "u1"},
            "b": {"model": "m2", "score": 0.9, "size_class": "small", "contributor": "u2"},
            "c": {"model": "m3", "score": 0.7, "size_class": "medium", "contributor": "u3"},
        }
        lb = gm.build_leaderboard(adapters)
        assert set(lb.keys()) == {"small", "medium"}
        # small should be sorted descending
        assert lb["small"][0]["score"] == 0.9
        assert lb["small"][1]["score"] == 0.5
        # medium has one entry
        assert lb["medium"][0]["model"] == "m3"

    def test_skips_none_score(self):
        adapters = {
            "a": {"model": "m1", "score": None, "size_class": "small"},
            "b": {"model": "m2", "score": 0.6, "size_class": "small", "contributor": "u"},
        }
        lb = gm.build_leaderboard(adapters)
        assert len(lb["small"]) == 1
        assert lb["small"][0]["model"] == "m2"

    def test_empty_adapters(self):
        assert gm.build_leaderboard({}) == {}

    def test_all_none_scores(self):
        adapters = {
            "a": {"model": "m1", "score": None, "size_class": "small"},
        }
        assert gm.build_leaderboard(adapters) == {}

    def test_default_size_class_used(self):
        adapters = {
            "a": {"model": "m1", "score": 0.8, "contributor": "u"},
        }
        lb = gm.build_leaderboard(adapters)
        assert gm.DEFAULT_SIZE_CLASS in lb


# ---------------------------------------------------------------------------
# M. main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_writes_manifest_with_all_sections(self, monkeypatch, tmp_path):
        _patch_repo(monkeypatch, tmp_path)

        # Create a nerve
        nerve_dir = tmp_path / "nerves" / "test_nerve"
        nerve_dir.mkdir(parents=True)
        _write_json(str(nerve_dir / "bundle.json"), {
            "description": "A test nerve",
            "role": "tool",
            "tags": ["test"],
            "authors": [{"github": "tester"}],
            "version": "1.0",
            "tools": [{"name": "greet"}],
        })

        # Create an adapter
        ad = tmp_path / "adapters" / "tool" / "small" / "phi3"
        ad.mkdir(parents=True)
        _write_json(str(ad / "meta.json"), {
            "model": "phi3",
            "size_class": "small",
            "provider": "ollama",
            "contributor": {"github": "alice"},
        })
        _write_json(str(ad / "qualification.json"), {"overall_score": 0.88})

        # Create a tool
        td = tmp_path / "tools" / "greet"
        td.mkdir(parents=True)
        _write_json(str(td / "meta.json"), {
            "name": "greet",
            "version": "1.0.0",
            "description": "Greets a user by name",
            "implementations": {"python": "tool.py"},
            "author": {"github": "dev"},
            "category": "utils",
            "tags": ["greeting"],
            "parameters": [],
        })

        # Create an MCP
        md = tmp_path / "mcps" / "test_mcp"
        md.mkdir(parents=True)
        _write_json(str(md / "meta.json"), {
            "name": "test_mcp",
            "version": "0.1.0",
            "description": "A test MCP server for testing",
            "source": "npm",
            "package": "test-mcp",
            "command": ["npx", "test-mcp"],
            "auth_type": "none",
            "tools": ["do_test"],
            "capabilities": ["testing"],
            "category": "test",
        })

        # Create a connector
        cd = tmp_path / "connectors" / "test_conn"
        cd.mkdir(parents=True)
        _write_json(str(cd / "meta.json"), {
            "name": "test_conn",
            "version": "0.1.0",
            "description": "A test connector for testing",
            "language": "python",
            "platforms": ["test"],
            "author": {"github": "dev"},
            "capabilities": {"incoming": [], "outgoing": []},
            "config_fields": [],
        })

        gm.main()

        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Top-level keys
        assert manifest["version"] == "1.0"
        assert "generated_at" in manifest
        assert "test_nerve" in manifest["nerves"]
        assert "tool/small/phi3" in manifest["adapters"]
        assert "greet" in manifest["tools"]
        assert "test_mcp" in manifest["mcps"]
        assert "test_conn" in manifest["connectors"]

        # Stats
        assert manifest["stats"]["total_nerves"] == 1
        assert manifest["stats"]["total_adapters"] == 1
        assert manifest["stats"]["total_connectors"] == 1
        assert manifest["stats"]["total_tools"] == 1
        assert manifest["stats"]["total_mcps"] == 1

        # Leaderboard
        assert "small" in manifest["leaderboard"]
        assert manifest["leaderboard"]["small"][0]["model"] == "phi3"
        assert manifest["leaderboard"]["small"][0]["score"] == 0.88

    def test_empty_repo(self, monkeypatch, tmp_path):
        """main() should still produce a valid manifest when all dirs are empty."""
        _patch_repo(monkeypatch, tmp_path)
        for d in ("nerves", "adapters", "connectors", "tools", "mcps"):
            (tmp_path / d).mkdir()

        gm.main()

        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)

        assert manifest["nerves"] == {}
        assert manifest["adapters"] == {}
        assert manifest["connectors"] == {}
        assert manifest["tools"] == {}
        assert manifest["mcps"] == {}
        assert manifest["stats"]["total_nerves"] == 0
        assert manifest["leaderboard"] == {}
