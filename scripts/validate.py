#!/usr/bin/env python3
"""Schema validation for community contributions.

Validates all JSON files against their respective schemas.
Checks structural requirements for nerves, adapters, and connectors.
"""

import json
import os
import re
import sys
from functools import lru_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS_DIR = os.path.join(REPO_ROOT, "schemas")

# Unsafe patterns in tool files — checked per language
UNSAFE_PATTERNS_PYTHON = [
    (r"\bos\.system\b", "os.system"),
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\bsubprocess\b", "subprocess"),
    (r"\b__import__\s*\(", "__import__()"),
]

UNSAFE_PATTERNS_JS = [
    (r"\bchild_process\b", "child_process"),
    (r"\beval\s*\(", "eval()"),
    (r"\bFunction\s*\(", "Function() constructor"),
    (r"\bvm\.runIn", "vm.runInNewContext/vm.runInThisContext"),
    (r"\bexecSync\b", "execSync"),
    (r"\bspawnSync\b", "spawnSync"),
]


@lru_cache(maxsize=None)
def load_role_tuning_profiles() -> tuple:
    """Load role tuning profiles from the schemas directory.

    Returns a tuple of (roles_dict,) wrapped for lru_cache compatibility.
    The actual dict is accessed via the return value directly.
    """
    path = os.path.join(SCHEMAS_DIR, "role_tuning_profiles.json")
    with open(path) as f:
        return json.load(f).get("roles", {})


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    """Load and cache a JSON schema file by name from the schemas directory."""
    path = os.path.join(SCHEMAS_DIR, name)
    with open(path) as f:
        return json.load(f)


def load_json(path: str) -> dict | list | None:
    """Load a JSON file, returning None and printing an error on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR: Cannot parse {path}: {e}")
        return None


def _validate_with_jsonschema(data: dict | list, schema: dict, filepath: str) -> list[str] | None:
    """Attempt validation using the jsonschema library.

    Returns a list of errors if jsonschema is available, or None if not installed.
    """
    try:
        import jsonschema
    except ImportError:
        return None

    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(data):
        path_str = "/".join(str(p) for p in error.absolute_path)
        errors.append(f"  {filepath}: {error.message} (at {path_str})")
    return errors


def _validate_fallback_object(data: dict, schema: dict, filepath: str) -> list[str]:
    """Fallback validation for object types: check required fields and enums."""
    errors = []
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"  {filepath}: missing required field '{field}'")
    for field, prop in schema.get("properties", {}).items():
        if field not in data or "enum" not in prop:
            continue
        if data[field] not in prop["enum"]:
            errors.append(f"  {filepath}: '{field}' must be one of {prop['enum']}, got '{data[field]}'")
    return errors


def _validate_fallback_array(data: list, schema: dict, filepath: str) -> list[str]:
    """Fallback validation for array types: check minItems constraint."""
    min_items = schema.get("minItems", 0)
    if len(data) < min_items:
        return [f"  {filepath}: array must have at least {min_items} items, got {len(data)}"]
    return []


def validate_json_against_schema(data: dict | list, schema: dict, filepath: str) -> list[str]:
    """Validate data against a JSON schema.

    Checks required fields, types, and enum constraints.
    Uses jsonschema library if available, otherwise falls back to manual checks.
    """
    result = _validate_with_jsonschema(data, schema, filepath)
    if result is not None:
        return result

    if schema.get("type") == "object" and isinstance(data, dict):
        return _validate_fallback_object(data, schema, filepath)
    if schema.get("type") == "array" and isinstance(data, list):
        return _validate_fallback_array(data, schema, filepath)
    return []


def check_tool_safety(filepath: str) -> list[str]:
    """Check a tool file for unsafe patterns based on its language."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except OSError:
        return []

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".py":
        patterns = UNSAFE_PATTERNS_PYTHON
    elif ext in (".js", ".ts", ".mjs"):
        patterns = UNSAFE_PATTERNS_JS
    else:
        return []

    return [
        f"  UNSAFE: {filepath} contains {name}"
        for pattern, name in patterns
        if re.search(pattern, content)
    ]


def _validate_nerve_bundle(nerve_dir: str, name: str) -> tuple[list[str], dict | None]:
    """Validate the bundle.json file in a nerve directory.

    Returns a tuple of (errors, bundle_data). bundle_data is None if missing or invalid.
    """
    bundle_path = os.path.join(nerve_dir, "bundle.json")
    if not os.path.exists(bundle_path):
        return ([f"  {name}: missing bundle.json"], None)

    bundle = load_json(bundle_path)
    if bundle is None:
        return ([], None)

    schema = load_schema("bundle.schema.json")
    errors = validate_json_against_schema(bundle, schema, bundle_path)
    return (errors, bundle)


def _validate_nerve_tests(nerve_dir: str, name: str) -> list[str]:
    """Validate test_cases.json in a nerve directory for structure and required test types."""
    tests_path = os.path.join(nerve_dir, "test_cases.json")
    if not os.path.exists(tests_path):
        return [f"  {name}: missing test_cases.json"]

    tests = load_json(tests_path)
    if tests is None:
        return []

    errors = []
    test_schema = load_schema("test_cases.schema.json")
    errors.extend(validate_json_against_schema(tests, test_schema, tests_path))

    types = [t.get("type") for t in tests if isinstance(t, dict)]
    if "core" not in types:
        errors.append(f"  {name}: test_cases.json must have at least 1 'core' test")
    if "negative" not in types:
        errors.append(f"  {name}: test_cases.json must have at least 1 'negative' test")
    return errors


def _validate_nerve_tools(nerve_dir: str, name: str, bundle: dict) -> list[str]:
    """Validate tool specs and implementations referenced from a nerve bundle."""
    errors = []
    for tool in bundle.get("tools", []):
        tool_name = tool.get("name", "")
        errors.extend(_validate_nerve_tool_spec(nerve_dir, name, tool, tool_name))
        errors.extend(_validate_nerve_tool_impls(nerve_dir, name, tool, tool_name))
    return errors


def _validate_nerve_tool_spec(nerve_dir: str, name: str, tool: dict, tool_name: str) -> list[str]:
    """Validate a single tool's spec file exists and conforms to schema."""
    spec_path = os.path.join(nerve_dir, tool.get("spec", ""))
    if not os.path.exists(spec_path):
        return [f"  {name}: tool '{tool_name}' missing spec at {tool.get('spec', '')}"]

    spec = load_json(spec_path)
    if spec is None:
        return []

    spec_schema = load_schema("tool_spec.schema.json")
    return validate_json_against_schema(spec, spec_schema, spec_path)


def _validate_nerve_tool_impls(nerve_dir: str, name: str, tool: dict, tool_name: str) -> list[str]:
    """Validate that a tool's implementation files exist and are safe."""
    errors = []
    for lang, impl_path in tool.get("implementations", {}).items():
        full_path = os.path.join(nerve_dir, impl_path)
        if not os.path.exists(full_path):
            errors.append(f"  {name}: tool '{tool_name}' missing {lang} implementation at {impl_path}")
        else:
            errors.extend(check_tool_safety(full_path))
    return errors


def validate_nerve(nerve_dir: str) -> list[str]:
    """Validate a nerve bundle directory."""
    name = os.path.basename(nerve_dir)

    bundle_errors, bundle = _validate_nerve_bundle(nerve_dir, name)
    if bundle is None:
        return bundle_errors

    errors = list(bundle_errors)
    errors.extend(_validate_nerve_tests(nerve_dir, name))
    errors.extend(_validate_nerve_tools(nerve_dir, name, bundle))
    return errors


def _validate_adapter_required_files(adapter_dir: str, name: str) -> list[str]:
    """Validate required files (meta.json, context.json) in an adapter directory."""
    errors = []
    for required, schema_name in [
        ("meta.json", "adapter_meta.schema.json"),
        ("context.json", "adapter_context.schema.json"),
    ]:
        path = os.path.join(adapter_dir, required)
        if not os.path.exists(path):
            errors.append(f"  {name}: missing {required}")
            continue
        data = load_json(path)
        if data is not None:
            schema = load_schema(schema_name)
            errors.extend(validate_json_against_schema(data, schema, path))
    return errors


def _validate_adapter_qualification(adapter_dir: str, name: str) -> list[str]:
    """Validate optional qualification.json against schema and score range."""
    qual_path = os.path.join(adapter_dir, "qualification.json")
    if not os.path.exists(qual_path):
        return []

    qual = load_json(qual_path)
    if qual is None:
        return []

    errors = []
    schema = load_schema("adapter_qualification.schema.json")
    errors.extend(validate_json_against_schema(qual, schema, qual_path))

    if not isinstance(qual, dict):
        return errors

    score = qual.get("overall_score", -1)
    if not (0.0 <= score <= 1.0):
        errors.append(f"  {name}: qualification score must be 0.0-1.0, got {score}")
    return errors


def _validate_adapter_size_class(adapter_dir: str, name: str, meta: dict) -> list[str]:
    """Validate that the size_class field in meta.json is a recognized value."""
    sc = meta.get("size_class", "")
    if sc and sc not in ("tinylm", "small", "medium", "large"):
        return [f"  {name}: invalid size_class '{sc}'"]
    return []


def _validate_adapter_tuning(adapter_dir: str, name: str, meta: dict) -> list[str]:
    """Validate tuning target_modules and lora_rank against the role profile."""
    tuning = meta.get("tuning", {})
    if not tuning:
        return []

    role = os.path.basename(os.path.dirname(adapter_dir))
    profiles = load_role_tuning_profiles()
    profile = profiles.get(role)
    if not profile:
        return []

    errors = []
    errors.extend(_validate_tuning_target_modules(name, role, tuning, profile))
    errors.extend(_validate_tuning_lora_rank(name, role, tuning, profile))
    return errors


def _validate_tuning_target_modules(name: str, role: str, tuning: dict, profile: dict) -> list[str]:
    """Check that lora_target_modules are in the allowed set for the role."""
    target_modules = tuning.get("lora_target_modules", [])
    allowed = set(profile.get("allowed_target_modules", []))
    return [
        f"  {name}: lora_target_module '{mod}' not allowed for role '{role}'. "
        f"Allowed: {sorted(allowed)}"
        for mod in target_modules
        if mod not in allowed
    ]


def _validate_tuning_lora_rank(name: str, role: str, tuning: dict, profile: dict) -> list[str]:
    """Check that lora_rank does not exceed the maximum for the role."""
    rank = tuning.get("lora_rank", 0)
    max_rank = profile.get("max_lora_rank", 999)
    if rank > max_rank:
        return [f"  {name}: lora_rank {rank} exceeds max {max_rank} for role '{role}'"]
    return []


def validate_adapter(adapter_dir: str) -> list[str]:
    """Validate a brain adapter directory."""
    name = os.path.basename(adapter_dir)

    errors = _validate_adapter_required_files(adapter_dir, name)
    errors.extend(_validate_adapter_qualification(adapter_dir, name))

    meta_path = os.path.join(adapter_dir, "meta.json")
    meta = load_json(meta_path) if os.path.exists(meta_path) else None
    if not meta or not isinstance(meta, dict):
        return errors

    errors.extend(_validate_adapter_size_class(adapter_dir, name, meta))
    errors.extend(_validate_adapter_tuning(adapter_dir, name, meta))
    return errors


def validate_tool(tool_dir: str) -> list[str]:
    """Validate a community tool directory for required files, schema, and safety."""
    errors = []
    name = os.path.basename(tool_dir)

    errors.extend(_validate_tool_meta(tool_dir, name))
    errors.extend(_validate_tool_implementations(tool_dir, name))
    errors.extend(_validate_tool_tests(tool_dir, name))

    readme_path = os.path.join(tool_dir, "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"  {name}: missing README.md")

    return errors


def _validate_tool_meta(tool_dir: str, name: str) -> list[str]:
    """Validate that meta.json exists and conforms to the tool_meta schema."""
    meta_path = os.path.join(tool_dir, "meta.json")
    if not os.path.exists(meta_path):
        return [f"  {name}: missing meta.json"]

    meta = load_json(meta_path)
    if meta is None:
        return []

    schema = load_schema("tool_meta.schema.json")
    return validate_json_against_schema(meta, schema, meta_path)


def _validate_tool_implementations(tool_dir: str, name: str) -> list[str]:
    """Validate that tool implementations listed in meta.json exist and are safe."""
    meta_path = os.path.join(tool_dir, "meta.json")
    meta = load_json(meta_path) if os.path.exists(meta_path) else None
    implementations = meta.get("implementations", {}) if meta else {}

    if not implementations:
        return [f"  {name}: no implementations listed in meta.json"]

    errors = []
    for lang, impl_file in implementations.items():
        impl_path = os.path.join(tool_dir, impl_file)
        if not os.path.exists(impl_path):
            errors.append(f"  {name}: missing {lang} implementation: {impl_file}")
        else:
            errors.extend(check_tool_safety(impl_path))
    return errors


def _validate_tool_tests(tool_dir: str, name: str) -> list[str]:
    """Validate that tests.json exists and conforms to the tool_tests schema."""
    tests_path = os.path.join(tool_dir, "tests.json")
    if not os.path.exists(tests_path):
        return [f"  {name}: missing tests.json"]

    tests = load_json(tests_path)
    if tests is None:
        return []

    tests_schema = load_schema("tool_tests.schema.json")
    return validate_json_against_schema(tests, tests_schema, tests_path)


def validate_mcp(mcp_dir: str) -> list[str]:
    """Validate an external MCP server directory for required meta.json and README."""
    errors = []
    name = os.path.basename(mcp_dir)

    meta_path = os.path.join(mcp_dir, "meta.json")
    if not os.path.exists(meta_path):
        errors.append(f"  {name}: missing meta.json")
    else:
        meta = load_json(meta_path)
        if meta is not None:
            schema = load_schema("mcp_meta.schema.json")
            errors.extend(validate_json_against_schema(meta, schema, meta_path))

    readme_path = os.path.join(mcp_dir, "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"  {name}: missing README.md")

    return errors


def validate_connector(connector_dir: str) -> list[str]:
    """Validate a connector directory for required files and implementation."""
    errors = []
    name = os.path.basename(connector_dir)

    meta_path = os.path.join(connector_dir, "meta.json")
    if not os.path.exists(meta_path):
        errors.append(f"  {name}: missing meta.json")
    else:
        meta = load_json(meta_path)
        if meta is not None:
            schema = load_schema("connector_meta.schema.json")
            errors.extend(validate_json_against_schema(meta, schema, meta_path))

    config_path = os.path.join(connector_dir, "config-template.json")
    if not os.path.exists(config_path):
        errors.append(f"  {name}: missing config-template.json")

    readme_path = os.path.join(connector_dir, "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"  {name}: missing README.md")

    has_impl = any(
        f.startswith("connector.") for f in os.listdir(connector_dir) if os.path.isfile(os.path.join(connector_dir, f))
    )
    if not has_impl:
        errors.append(f"  {name}: missing connector implementation (connector.js or connector.py)")

    return errors


def _collect_subdirs(parent: str) -> list[str]:
    """Return sorted subdirectory names within a parent directory."""
    if not os.path.isdir(parent):
        return []
    return [
        name for name in sorted(os.listdir(parent))
        if os.path.isdir(os.path.join(parent, name))
    ]


def _validate_all_nerves() -> list[str]:
    """Validate all nerve bundles in the nerves/ directory."""
    errors = []
    nerves_dir = os.path.join(REPO_ROOT, "nerves")
    for name in _collect_subdirs(nerves_dir):
        print(f"Validating nerve: {name}")
        errors.extend(validate_nerve(os.path.join(nerves_dir, name)))
    return errors


def _validate_all_adapters() -> list[str]:
    """Validate all adapters across roles, size classes, and model-specific dirs."""
    errors = []
    adapters_root = os.path.join(REPO_ROOT, "adapters")
    for role in _collect_subdirs(adapters_root):
        role_dir = os.path.join(adapters_root, role)
        for size_class in _collect_subdirs(role_dir):
            size_dir = os.path.join(role_dir, size_class)
            print(f"Validating adapter: {role}/{size_class}")
            errors.extend(validate_adapter(size_dir))
            for model_name in _collect_subdirs(size_dir):
                print(f"Validating adapter: {role}/{size_class}/{model_name}")
                errors.extend(validate_adapter(os.path.join(size_dir, model_name)))
    return errors


def _validate_all_connectors() -> list[str]:
    """Validate all connectors in the connectors/ directory."""
    errors = []
    connectors_dir = os.path.join(REPO_ROOT, "connectors")
    for name in _collect_subdirs(connectors_dir):
        print(f"Validating connector: {name}")
        errors.extend(validate_connector(os.path.join(connectors_dir, name)))
    return errors


def _validate_all_tools() -> list[str]:
    """Validate all tools in the mcp_tools/ directory."""
    errors = []
    tools_dir = os.path.join(REPO_ROOT, "mcp_tools")
    for name in _collect_subdirs(tools_dir):
        print(f"Validating tool: {name}")
        errors.extend(validate_tool(os.path.join(tools_dir, name)))
    return errors


def _validate_all_mcps() -> list[str]:
    """Validate all external MCP servers in the mcps/ directory."""
    errors = []
    mcps_dir = os.path.join(REPO_ROOT, "mcps")
    for name in _collect_subdirs(mcps_dir):
        print(f"Validating mcp: {name}")
        errors.extend(validate_mcp(os.path.join(mcps_dir, name)))
    return errors


def _get_changed_dirs() -> set[str] | None:
    """Get top-level contribution directories affected by this PR.

    Returns a set of directory paths (e.g. 'nerves/math_nerve',
    'adapters/brain/medium/qwen2.5-coder-7b') that were changed
    relative to origin/main. Returns None if not in a PR context
    or git diff fails — callers should fall back to full validation.
    """
    import subprocess as _sp
    try:
        result = _sp.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
    except Exception:
        return None

    changed = set()
    for path in result.stdout.strip().splitlines():
        parts = path.split("/")
        if len(parts) < 2:
            continue
        top = parts[0]
        if top == "nerves":
            changed.add(os.path.join(REPO_ROOT, "nerves", parts[1]))
        elif top == "adapters" and len(parts) >= 3:
            # adapters/{role}/{size_class}/... — validate that size dir
            adapter_dir = os.path.join(REPO_ROOT, *parts[:3])
            changed.add(adapter_dir)
            # If model-specific: adapters/{role}/{size}/{model}/...
            if len(parts) >= 4 and not parts[3].endswith(".json"):
                changed.add(os.path.join(REPO_ROOT, *parts[:4]))
        elif top == "mcp_tools":
            changed.add(os.path.join(REPO_ROOT, "mcp_tools", parts[1]))
        elif top == "connectors":
            changed.add(os.path.join(REPO_ROOT, "connectors", parts[1]))
        elif top == "mcps":
            changed.add(os.path.join(REPO_ROOT, "mcps", parts[1]))
    return changed


def _validate_changed_only(changed_dirs: set[str]) -> list[str]:
    """Validate only the directories that changed in this PR."""
    errors = []
    for d in sorted(changed_dirs):
        if not os.path.isdir(d):
            continue
        parts = os.path.relpath(d, REPO_ROOT).split(os.sep)
        top = parts[0]
        name = parts[-1]
        print(f"Validating changed: {os.path.relpath(d, REPO_ROOT)}")
        if top == "nerves":
            errors.extend(validate_nerve(d))
        elif top == "adapters":
            errors.extend(validate_adapter(d))
        elif top == "mcp_tools":
            errors.extend(validate_tool(d))
        elif top == "connectors":
            errors.extend(validate_connector(d))
        elif top == "mcps":
            errors.extend(validate_mcp(d))
    return errors


def main():
    """Run validations and exit with status code 1 on failure, 0 on success.

    In PR context (--changed-only or auto-detected from git diff),
    only validates files affected by the PR. Otherwise validates everything.
    """
    changed_only = "--changed-only" in sys.argv

    if changed_only:
        changed = _get_changed_dirs()
        if changed:
            print(f"PR mode: validating {len(changed)} changed dir(s)")
            errors = _validate_changed_only(changed)
        else:
            print("Could not determine changed files, falling back to full validation")
            errors = _validate_all()
    else:
        errors = _validate_all()

    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\nAll validations passed.")
        sys.exit(0)


def _validate_all() -> list[str]:
    """Run full-repo validation across all contribution types."""
    errors = []
    errors.extend(_validate_all_nerves())
    errors.extend(_validate_all_adapters())
    errors.extend(_validate_all_connectors())
    errors.extend(_validate_all_tools())
    errors.extend(_validate_all_mcps())
    return errors


if __name__ == "__main__":
    main()
