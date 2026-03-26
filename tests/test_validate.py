"""Comprehensive tests for scripts/validate.py."""

import json
import os
import sys

import pytest

# conftest helpers — pytest makes conftest importable within the tests package
from tests.conftest import (
    make_adapter_dir,
    make_connector_dir,
    make_mcp_dir,
    make_nerve_dir,
    make_tool_dir,
)


# ========================================================================
# A. JSON loading
# ========================================================================


class TestLoadJson:
    """Tests for validate.load_json."""

    def test_valid_json(self, tmp_path, patched_validate):
        p = tmp_path / "ok.json"
        p.write_text('{"a": 1}')
        assert patched_validate.load_json(str(p)) == {"a": 1}

    def test_invalid_json(self, tmp_path, patched_validate, capsys):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        result = patched_validate.load_json(str(p))
        assert result is None
        assert "ERROR" in capsys.readouterr().out

    def test_missing_file(self, patched_validate, capsys):
        result = patched_validate.load_json("/nonexistent/path.json")
        assert result is None
        assert "ERROR" in capsys.readouterr().out


class TestLoadSchema:
    """Tests for validate.load_schema (with caching)."""

    def test_loads_known_schema(self, patched_validate):
        schema = patched_validate.load_schema("bundle.schema.json")
        assert schema["title"] == "Nerve Bundle"

    def test_caches_result(self, patched_validate):
        s1 = patched_validate.load_schema("bundle.schema.json")
        s2 = patched_validate.load_schema("bundle.schema.json")
        assert s1 is s2  # same object from cache


class TestLoadRoleTuningProfiles:
    """Tests for validate.load_role_tuning_profiles."""

    def test_loads_profiles(self, patched_validate):
        profiles = patched_validate.load_role_tuning_profiles()
        assert "brain" in profiles
        assert "min_temperature" in profiles["brain"]

    def test_caches_result(self, patched_validate):
        p1 = patched_validate.load_role_tuning_profiles()
        p2 = patched_validate.load_role_tuning_profiles()
        assert p1 is p2


# ========================================================================
# B. Schema validation
# ========================================================================


class TestValidateJsonAgainstSchema:
    """Tests for validate.validate_json_against_schema."""

    def test_valid_data(self, patched_validate):
        schema = patched_validate.load_schema("adapter_meta.schema.json")
        data = {
            "model": "llama3.2-3b",
            "size_class": "small",
            "contributor": {"github": "tester"},
        }
        errors = patched_validate.validate_json_against_schema(data, schema, "test.json")
        assert errors == []

    def test_missing_required_field(self, patched_validate):
        schema = patched_validate.load_schema("adapter_meta.schema.json")
        data = {"model": "llama3.2-3b"}  # missing size_class, contributor
        errors = patched_validate.validate_json_against_schema(data, schema, "test.json")
        assert len(errors) > 0

    def test_invalid_enum(self, patched_validate):
        schema = patched_validate.load_schema("adapter_meta.schema.json")
        data = {
            "model": "m",
            "size_class": "gigantic",  # not in enum
            "contributor": {"github": "t"},
        }
        errors = patched_validate.validate_json_against_schema(data, schema, "test.json")
        assert len(errors) > 0

    def test_fallback_array_min_items(self, patched_validate, monkeypatch):
        """Test fallback validator for arrays when jsonschema is absent."""
        # Force fallback by hiding jsonschema
        monkeypatch.setattr(
            patched_validate,
            "_validate_with_jsonschema",
            lambda data, schema, fp: None,
        )
        schema = {"type": "array", "minItems": 3}
        errors = patched_validate.validate_json_against_schema([1], schema, "f.json")
        assert len(errors) == 1
        assert "at least 3" in errors[0]

    def test_fallback_object_required(self, patched_validate, monkeypatch):
        """Test fallback validator for objects when jsonschema is absent."""
        monkeypatch.setattr(
            patched_validate,
            "_validate_with_jsonschema",
            lambda data, schema, fp: None,
        )
        schema = {"type": "object", "required": ["x", "y"]}
        errors = patched_validate.validate_json_against_schema({"x": 1}, schema, "f.json")
        assert len(errors) == 1
        assert "'y'" in errors[0]


# ========================================================================
# C. Tool safety
# ========================================================================


class TestCheckToolSafety:
    """Tests for validate.check_tool_safety."""

    def test_unsafe_python_os_system(self, tmp_path, patched_validate):
        p = tmp_path / "bad.py"
        p.write_text("import os\nos.system('rm -rf /')\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert any("os.system" in e for e in errors)

    def test_unsafe_python_eval(self, tmp_path, patched_validate):
        p = tmp_path / "bad.py"
        p.write_text("result = eval('1+1')\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert any("eval()" in e for e in errors)

    def test_unsafe_python_subprocess(self, tmp_path, patched_validate):
        p = tmp_path / "bad.py"
        p.write_text("import subprocess\nsubprocess.run(['ls'])\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert any("subprocess" in e for e in errors)

    def test_unsafe_js_child_process(self, tmp_path, patched_validate):
        p = tmp_path / "bad.js"
        p.write_text("const cp = require('child_process');\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert any("child_process" in e for e in errors)

    def test_unsafe_js_eval(self, tmp_path, patched_validate):
        p = tmp_path / "bad.js"
        p.write_text("let x = eval('1+1');\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert any("eval()" in e for e in errors)

    def test_clean_python(self, tmp_path, patched_validate):
        p = tmp_path / "clean.py"
        p.write_text("def run():\n    return 42\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert errors == []

    def test_clean_js(self, tmp_path, patched_validate):
        p = tmp_path / "clean.js"
        p.write_text("function run() { return 42; }\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert errors == []

    def test_non_code_file(self, tmp_path, patched_validate):
        p = tmp_path / "data.txt"
        p.write_text("os.system('bad')\n")
        errors = patched_validate.check_tool_safety(str(p))
        assert errors == []

    def test_missing_file(self, patched_validate):
        errors = patched_validate.check_tool_safety("/nonexistent/file.py")
        assert errors == []


# ========================================================================
# D. Nerve validation
# ========================================================================


class TestValidateNerve:
    """Tests for validate.validate_nerve."""

    def test_valid_nerve(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(mock_repo / "nerves", "good_nerve")
        errors = patched_validate.validate_nerve(str(nerve))
        assert errors == []

    def test_missing_bundle(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(mock_repo / "nerves", "no_bundle", skip_bundle=True)
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("missing bundle.json" in e for e in errors)

    def test_invalid_bundle_schema(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "bad_bundle",
            bundle_overrides={"name": "bad_bundle"},
        )
        # Remove a required field to make schema invalid
        bundle_path = nerve / "bundle.json"
        bundle = json.loads(bundle_path.read_text())
        del bundle["role"]
        bundle_path.write_text(json.dumps(bundle))
        errors = patched_validate.validate_nerve(str(nerve))
        assert len(errors) > 0

    def test_missing_core_test(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "no_core",
            test_cases_overrides=[
                {"input": "a", "output": "b", "category": "negative", "type": "negative"},
                {"input": "c", "output": "d", "category": "edge", "type": "edge"},
                {"input": "e", "output": "f", "category": "boundary", "type": "boundary"},
                {"input": "g", "output": "h", "category": "boundary", "type": "boundary"},
            ],
        )
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("'core' test" in e for e in errors)

    def test_missing_negative_test(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "no_neg",
            test_cases_overrides=[
                {"input": "a", "output": "b", "category": "core", "type": "core"},
                {"input": "c", "output": "d", "category": "edge", "type": "edge"},
                {"input": "e", "output": "f", "category": "boundary", "type": "boundary"},
                {"input": "g", "output": "h", "category": "boundary", "type": "boundary"},
            ],
        )
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("'negative' test" in e for e in errors)

    def test_missing_test_cases_file(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves", "no_tests", skip_test_cases=True
        )
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("missing test_cases.json" in e for e in errors)

    def test_missing_tool_spec(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "bad_tool",
            tools=[
                {
                    "name": "my_tool",
                    "spec": "specs/my_tool.json",
                    "implementations": {},
                }
            ],
        )
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("missing spec" in e for e in errors)

    def test_tool_with_valid_spec(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "good_tool_nerve",
            tools=[
                {
                    "name": "my_tool",
                    "spec": "specs/my_tool.json",
                    "implementations": {"python": "mcp_tools/my_tool.py"},
                }
            ],
        )
        # Create the spec file
        (nerve / "specs").mkdir()
        spec = {
            "name": "my_tool",
            "description": "A test tool that does something useful",
            "parameters": [
                {"name": "q", "type": "string", "description": "query param"}
            ],
        }
        (nerve / "specs" / "my_tool.json").write_text(json.dumps(spec))
        # Create the implementation file
        (nerve / "mcp_tools").mkdir()
        (nerve / "mcp_tools" / "my_tool.py").write_text("def run(): pass\n")

        errors = patched_validate.validate_nerve(str(nerve))
        assert errors == []

    def test_tool_missing_implementation(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "missing_impl",
            tools=[
                {
                    "name": "my_tool",
                    "spec": "specs/my_tool.json",
                    "implementations": {"python": "mcp_tools/my_tool.py"},
                }
            ],
        )
        (nerve / "specs").mkdir()
        spec = {
            "name": "my_tool",
            "description": "A test tool that does something useful",
            "parameters": [],
        }
        (nerve / "specs" / "my_tool.json").write_text(json.dumps(spec))
        # Do NOT create the implementation file
        errors = patched_validate.validate_nerve(str(nerve))
        assert any("missing python implementation" in e for e in errors)

    def test_tool_unsafe_implementation(self, patched_validate, mock_repo):
        nerve = make_nerve_dir(
            mock_repo / "nerves",
            "unsafe_impl",
            tools=[
                {
                    "name": "my_tool",
                    "spec": "specs/my_tool.json",
                    "implementations": {"python": "mcp_tools/my_tool.py"},
                }
            ],
        )
        (nerve / "specs").mkdir()
        spec = {
            "name": "my_tool",
            "description": "A test tool that does something useful",
            "parameters": [],
        }
        (nerve / "specs" / "my_tool.json").write_text(json.dumps(spec))
        (nerve / "mcp_tools").mkdir()
        (nerve / "mcp_tools" / "my_tool.py").write_text("os.system('rm -rf /')\n")

        errors = patched_validate.validate_nerve(str(nerve))
        assert any("UNSAFE" in e for e in errors)


# ========================================================================
# E. Adapter validation
# ========================================================================


class TestValidateAdapter:
    """Tests for validate.validate_adapter."""

    def test_valid_adapter(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(mock_repo / "adapters", "good_adapter")
        errors = patched_validate.validate_adapter(str(adapter))
        assert errors == []

    def test_missing_meta(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(
            mock_repo / "adapters", "no_meta", skip_meta=True
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert any("missing meta.json" in e for e in errors)

    def test_missing_context(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(
            mock_repo / "adapters", "no_ctx", skip_context=True
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert any("missing context.json" in e for e in errors)

    def test_invalid_qualification_score(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(
            mock_repo / "adapters",
            "bad_qual",
            qualification_overrides={
                "overall_score": 1.5,  # out of range
                "test_count": 10,
                "pass_count": 8,
            },
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert any("qualification score" in e for e in errors)

    def test_valid_qualification(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(
            mock_repo / "adapters",
            "ok_qual",
            qualification_overrides={
                "overall_score": 0.85,
                "test_count": 10,
                "pass_count": 8,
            },
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert errors == []

    def test_invalid_size_class(self, patched_validate, mock_repo):
        adapter = make_adapter_dir(
            mock_repo / "adapters",
            "bad_sc",
            meta_overrides={"size_class": "gigantic"},
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert any("invalid size_class" in e for e in errors)

    def test_valid_size_classes(self, patched_validate, mock_repo):
        for sc in ("tinylm", "small", "medium", "large"):
            adapter = make_adapter_dir(
                mock_repo / "adapters",
                f"sc_{sc}",
                meta_overrides={"size_class": sc},
            )
            errors = patched_validate.validate_adapter(str(adapter))
            assert not any("invalid size_class" in e for e in errors), f"size_class {sc} should be valid"

    def test_tuning_temperature_out_of_range(self, patched_validate, mock_repo):
        """Adapter under brain/ role with temperature above 0.5 should fail."""
        role_dir = mock_repo / "adapters" / "brain"
        role_dir.mkdir(parents=True, exist_ok=True)
        adapter = make_adapter_dir(
            role_dir,
            "bad_temp",
            meta_overrides={
                "tuning": {
                    "temperature_range": [0.1, 0.3, 0.9],  # 0.9 exceeds brain max of 0.5
                }
            },
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert any("temperature_range" in e and "out of allowed bounds" in e for e in errors)

    def test_tuning_temperature_valid_for_role(self, patched_validate, mock_repo):
        """Adapter under creative/ role with high temperature should be fine."""
        role_dir = mock_repo / "adapters" / "creative"
        role_dir.mkdir(parents=True, exist_ok=True)
        adapter = make_adapter_dir(
            role_dir,
            "good_creative",
            meta_overrides={
                "tuning": {
                    "temperature_range": [0.5, 0.7, 0.9],  # within creative bounds
                }
            },
        )
        errors = patched_validate.validate_adapter(str(adapter))
        assert not any("temperature_range" in e for e in errors)


# ========================================================================
# F. Connector validation
# ========================================================================


class TestValidateConnector:
    """Tests for validate.validate_connector."""

    def test_valid_connector(self, patched_validate, mock_repo):
        conn = make_connector_dir(mock_repo / "connectors", "good_conn")
        errors = patched_validate.validate_connector(str(conn))
        assert errors == []

    def test_missing_meta(self, patched_validate, mock_repo):
        conn = make_connector_dir(
            mock_repo / "connectors", "no_meta", skip_meta=True
        )
        errors = patched_validate.validate_connector(str(conn))
        assert any("missing meta.json" in e for e in errors)

    def test_missing_config_template(self, patched_validate, mock_repo):
        conn = make_connector_dir(
            mock_repo / "connectors", "no_cfg", skip_config=True
        )
        errors = patched_validate.validate_connector(str(conn))
        assert any("missing config-template.json" in e for e in errors)

    def test_missing_readme(self, patched_validate, mock_repo):
        conn = make_connector_dir(
            mock_repo / "connectors", "no_readme", skip_readme=True
        )
        errors = patched_validate.validate_connector(str(conn))
        assert any("missing README.md" in e for e in errors)

    def test_missing_implementation(self, patched_validate, mock_repo):
        conn = make_connector_dir(
            mock_repo / "connectors", "no_impl", skip_impl=True
        )
        errors = patched_validate.validate_connector(str(conn))
        assert any("missing connector implementation" in e for e in errors)

    def test_invalid_meta_schema(self, patched_validate, mock_repo):
        conn = make_connector_dir(
            mock_repo / "connectors",
            "bad_meta",
            meta_overrides={
                "name": "bad-meta",
                "version": "1.0.0",
                "description": "A connector with invalid schema data",
                "language": "cobol",  # not in enum
                "platforms": ["linux"],
                "author": {"github": "t"},
                "capabilities": {"incoming": [], "outgoing": []},
                "config_fields": [],
                "redis_channels": {"subscribe": [], "publish": []},
            },
        )
        errors = patched_validate.validate_connector(str(conn))
        assert len(errors) > 0


# ========================================================================
# G. MCP validation
# ========================================================================


class TestValidateMcp:
    """Tests for validate.validate_mcp."""

    def test_valid_mcp(self, patched_validate, mock_repo):
        mcp = make_mcp_dir(mock_repo / "mcps", "good_mcp")
        errors = patched_validate.validate_mcp(str(mcp))
        assert errors == []

    def test_missing_meta(self, patched_validate, mock_repo):
        mcp = make_mcp_dir(mock_repo / "mcps", "no_meta", skip_meta=True)
        errors = patched_validate.validate_mcp(str(mcp))
        assert any("missing meta.json" in e for e in errors)

    def test_missing_readme(self, patched_validate, mock_repo):
        mcp = make_mcp_dir(mock_repo / "mcps", "no_readme", skip_readme=True)
        errors = patched_validate.validate_mcp(str(mcp))
        assert any("missing README.md" in e for e in errors)

    def test_invalid_meta_schema(self, patched_validate, mock_repo):
        mcp = make_mcp_dir(
            mock_repo / "mcps",
            "bad_mcp",
            meta_overrides={
                "source": "pypi",  # not in enum
            },
        )
        errors = patched_validate.validate_mcp(str(mcp))
        assert len(errors) > 0


# ========================================================================
# H. Tool validation
# ========================================================================


class TestValidateTool:
    """Tests for validate.validate_tool."""

    def test_valid_tool(self, patched_validate, mock_repo):
        tool = make_tool_dir(mock_repo / "mcp_tools", "good_tool")
        errors = patched_validate.validate_tool(str(tool))
        assert errors == []

    def test_missing_meta(self, patched_validate, mock_repo):
        tool = make_tool_dir(mock_repo / "mcp_tools", "no_meta", skip_meta=True)
        errors = patched_validate.validate_tool(str(tool))
        assert any("missing meta.json" in e for e in errors)

    def test_missing_readme(self, patched_validate, mock_repo):
        tool = make_tool_dir(mock_repo / "mcp_tools", "no_readme", skip_readme=True)
        errors = patched_validate.validate_tool(str(tool))
        assert any("missing README.md" in e for e in errors)

    def test_missing_implementation(self, patched_validate, mock_repo):
        tool = make_tool_dir(mock_repo / "mcp_tools", "no_impl", skip_impl=True)
        errors = patched_validate.validate_tool(str(tool))
        assert any("missing python implementation" in e for e in errors)

    def test_missing_tests_json(self, patched_validate, mock_repo):
        tool = make_tool_dir(mock_repo / "mcp_tools", "no_tests", skip_tests=True)
        errors = patched_validate.validate_tool(str(tool))
        assert any("missing tests.json" in e for e in errors)

    def test_unsafe_implementation(self, patched_validate, mock_repo):
        tool = make_tool_dir(
            mock_repo / "mcp_tools",
            "unsafe_tool",
            impl_content="import os\nos.system('rm -rf /')\n",
        )
        errors = patched_validate.validate_tool(str(tool))
        assert any("UNSAFE" in e for e in errors)

    def test_no_implementations_listed(self, patched_validate, mock_repo):
        tool = make_tool_dir(
            mock_repo / "mcp_tools",
            "empty_impls",
            meta_overrides={"implementations": {}},
        )
        errors = patched_validate.validate_tool(str(tool))
        assert any("no implementations" in e for e in errors)


# ========================================================================
# I. main() integration
# ========================================================================


class TestMain:
    """Tests for validate.main end-to-end."""

    def test_exits_0_on_valid_repo(self, patched_validate, mock_repo):
        """Empty repo with no items in any directory passes validation."""
        with pytest.raises(SystemExit) as exc_info:
            patched_validate.main()
        assert exc_info.value.code == 0

    def test_exits_1_on_errors(self, patched_validate, mock_repo):
        """A nerve with missing bundle causes exit code 1."""
        nerve = mock_repo / "nerves" / "broken"
        nerve.mkdir()
        # No bundle.json -> error
        with pytest.raises(SystemExit) as exc_info:
            patched_validate.main()
        assert exc_info.value.code == 1

    def test_validates_all_component_types(self, patched_validate, mock_repo):
        """Populate every component type and verify main exits 0."""
        make_nerve_dir(mock_repo / "nerves", "my_nerve")
        # adapters need role/size_class hierarchy
        role_dir = mock_repo / "adapters" / "brain"
        role_dir.mkdir(parents=True)
        sc_dir = role_dir / "small"
        make_adapter_dir(role_dir, "small")
        make_connector_dir(mock_repo / "connectors", "my_conn")
        make_mcp_dir(mock_repo / "mcps", "my_mcp")
        make_tool_dir(mock_repo / "mcp_tools", "my_tool")

        with pytest.raises(SystemExit) as exc_info:
            patched_validate.main()
        assert exc_info.value.code == 0

    def test_reports_multiple_errors(self, patched_validate, mock_repo, capsys):
        """Broken nerve + broken connector should accumulate errors."""
        broken_nerve = mock_repo / "nerves" / "broken_nerve"
        broken_nerve.mkdir()
        broken_conn = mock_repo / "connectors" / "broken_conn"
        broken_conn.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            patched_validate.main()
        assert exc_info.value.code == 1
        output = capsys.readouterr().out
        assert "VALIDATION FAILED" in output
