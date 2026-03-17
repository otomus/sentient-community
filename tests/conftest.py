"""Shared fixtures for sentient-community tests."""

import json
import os
import shutil

import pytest

# Real schemas directory for copying into temp dirs
_REAL_SCHEMAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas"
)


# ---------------------------------------------------------------------------
# Fixture: copy real schema files into tmp_path
# ---------------------------------------------------------------------------

@pytest.fixture()
def schemas_dir(tmp_path):
    """Copy all real schema files from schemas/ into a tmp_path/schemas dir."""
    dst = tmp_path / "schemas"
    shutil.copytree(_REAL_SCHEMAS_DIR, dst)
    return dst


# ---------------------------------------------------------------------------
# Fixture: minimal mock repo tree
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_repo(tmp_path):
    """Create a minimal repo tree with schemas/, nerves/, adapters/, connectors/, mcp_tools/, mcps/.

    Returns the tmp_path (repo root). All schema files are copied so that
    load_schema / load_role_tuning_profiles work correctly when SCHEMAS_DIR
    is patched.
    """
    for subdir in ("nerves", "adapters", "connectors", "mcp_tools", "mcps"):
        (tmp_path / subdir).mkdir()
    shutil.copytree(_REAL_SCHEMAS_DIR, tmp_path / "schemas")
    return tmp_path


# ---------------------------------------------------------------------------
# Fixture: patch REPO_ROOT / SCHEMAS_DIR on the validate module and clear caches
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_validate(mock_repo, monkeypatch):
    """Patch validate.REPO_ROOT and validate.SCHEMAS_DIR to use mock_repo.

    Also clears the lru_cache on load_schema and load_role_tuning_profiles
    before *and* after each test so cached state never leaks.
    """
    import validate

    validate.load_schema.cache_clear()
    validate.load_role_tuning_profiles.cache_clear()

    monkeypatch.setattr(validate, "REPO_ROOT", str(mock_repo))
    monkeypatch.setattr(validate, "SCHEMAS_DIR", str(mock_repo / "schemas"))

    yield validate

    validate.load_schema.cache_clear()
    validate.load_role_tuning_profiles.cache_clear()


# ---------------------------------------------------------------------------
# Helper: create a valid nerve directory
# ---------------------------------------------------------------------------

def make_nerve_dir(
    parent,
    name="test_nerve",
    *,
    bundle_overrides=None,
    test_cases_overrides=None,
    skip_test_cases=False,
    skip_bundle=False,
    tools=None,
):
    """Create a valid nerve directory under *parent*.

    Returns the path to the nerve directory.
    """
    nerve = parent / name
    nerve.mkdir(exist_ok=True)

    # -- bundle.json --
    if not skip_bundle:
        bundle = {
            "name": name,
            "version": "1.0",
            "description": "A test nerve for validation testing purposes",
            "role": "tool",
            "tags": ["test"],
            "authors": [{"github": "tester"}],
            "sentient_version": ">=0.1.0",
            "tools": tools or [],
            "default": {
                "system_prompt": "You are a test nerve.",
                "examples": [{"input": "hi", "output": "hello"}],
                "temperature": 0.7,
            },
        }
        if bundle_overrides:
            bundle.update(bundle_overrides)
        (nerve / "bundle.json").write_text(json.dumps(bundle))

    # -- test_cases.json --
    if not skip_test_cases:
        tests = test_cases_overrides or [
            {"input": "core input", "output": "core output", "category": "core", "type": "core"},
            {"input": "neg input", "output": "neg output", "category": "negative", "type": "negative"},
            {"input": "edge input", "output": "edge output", "category": "edge", "type": "edge"},
            {"input": "boundary input", "output": "boundary output", "category": "boundary", "type": "boundary"},
        ]
        (nerve / "test_cases.json").write_text(json.dumps(tests))

    return nerve


# ---------------------------------------------------------------------------
# Helper: create a valid adapter directory
# ---------------------------------------------------------------------------

def make_adapter_dir(
    parent,
    name="test_adapter",
    *,
    role_name="brain",
    meta_overrides=None,
    context_overrides=None,
    qualification_overrides=None,
    skip_meta=False,
    skip_context=False,
):
    """Create a valid adapter directory under *parent*.

    The adapter is placed at parent/name (the caller is responsible for
    creating the role/ and size_class/ parent directories if needed for
    the tuning-profile tests).

    Returns the path to the adapter directory.
    """
    adapter = parent / name
    adapter.mkdir(parents=True, exist_ok=True)

    if not skip_meta:
        meta = {
            "model": "test-model-7b",
            "size_class": "small",
            "provider": "gguf",
            "contributor": {"github": "tester"},
            "description": "A test adapter for validation",
        }
        if meta_overrides:
            meta.update(meta_overrides)
        (adapter / "meta.json").write_text(json.dumps(meta))

    if not skip_context:
        context = {
            "system_prompt": "You are a helpful brain adapter for testing.",
            "temperature": 0.7,
        }
        if context_overrides:
            context.update(context_overrides)
        (adapter / "context.json").write_text(json.dumps(context))

    if qualification_overrides is not None:
        (adapter / "qualification.json").write_text(json.dumps(qualification_overrides))

    return adapter


# ---------------------------------------------------------------------------
# Helper: create a valid connector directory
# ---------------------------------------------------------------------------

def make_connector_dir(
    parent,
    name="test_connector",
    *,
    meta_overrides=None,
    skip_meta=False,
    skip_config=False,
    skip_readme=False,
    skip_impl=False,
):
    """Create a valid connector directory under *parent*."""
    conn = parent / name
    conn.mkdir(exist_ok=True)

    if not skip_meta:
        meta = {
            "name": "test-connector",
            "version": "1.0.0",
            "description": "A test connector for validation testing",
            "language": "python",
            "platforms": ["linux"],
            "author": {"github": "tester"},
            "capabilities": {"incoming": ["text"], "outgoing": ["text"]},
            "config_fields": [{"name": "token", "required": True}],
            "redis_channels": {"subscribe": ["in"], "publish": ["out"]},
        }
        if meta_overrides:
            meta.update(meta_overrides)
        (conn / "meta.json").write_text(json.dumps(meta))

    if not skip_config:
        (conn / "config-template.json").write_text(json.dumps({"token": ""}))

    if not skip_readme:
        (conn / "README.md").write_text("# Test Connector\n")

    if not skip_impl:
        (conn / "connector.py").write_text("# connector impl\n")

    return conn


# ---------------------------------------------------------------------------
# Helper: create a valid MCP directory
# ---------------------------------------------------------------------------

def make_mcp_dir(
    parent,
    name="test_mcp",
    *,
    meta_overrides=None,
    skip_meta=False,
    skip_readme=False,
):
    """Create a valid MCP server directory under *parent*."""
    mcp = parent / name
    mcp.mkdir(exist_ok=True)

    if not skip_meta:
        meta = {
            "name": "test_mcp",
            "version": "1.0.0",
            "description": "A test MCP server for validation testing",
            "source": "npm",
            "package": "@test/mcp-server",
            "command": ["npx", "-y", "@test/mcp-server"],
            "auth_type": "none",
            "tools": ["tool_a"],
            "capabilities": ["search"],
            "category": "testing",
        }
        if meta_overrides:
            meta.update(meta_overrides)
        (mcp / "meta.json").write_text(json.dumps(meta))

    if not skip_readme:
        (mcp / "README.md").write_text("# Test MCP\n")

    return mcp


# ---------------------------------------------------------------------------
# Helper: create a valid tool directory
# ---------------------------------------------------------------------------

def make_tool_dir(
    parent,
    name="test_tool",
    *,
    meta_overrides=None,
    skip_meta=False,
    skip_readme=False,
    skip_impl=False,
    skip_tests=False,
    impl_content="def run(**kwargs): return 'ok'\n",
):
    """Create a valid community tool directory under *parent*."""
    tool = parent / name
    tool.mkdir(exist_ok=True)

    if not skip_meta:
        meta = {
            "name": "test_tool",
            "version": "1.0.0",
            "description": "A test tool for validation testing purposes",
            "implementations": {"python": "tool.py"},
            "author": {"github": "tester"},
            "category": "testing",
            "tags": ["test"],
            "parameters": [
                {"name": "query", "type": "string", "description": "The search query"}
            ],
        }
        if meta_overrides:
            meta.update(meta_overrides)
        (tool / "meta.json").write_text(json.dumps(meta))

    if not skip_impl:
        (tool / "tool.py").write_text(impl_content)

    if not skip_readme:
        (tool / "README.md").write_text("# Test Tool\n")

    if not skip_tests:
        tests = [
            {"description": "Basic test case for validation", "args": {"query": "hello"}},
            {"description": "Another test case for validation", "args": {"query": "world"}},
        ]
        (tool / "tests.json").write_text(json.dumps(tests))

    return tool
