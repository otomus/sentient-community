#!/usr/bin/env python3
"""Schema validation for community contributions.

Validates all JSON files against their respective schemas.
Checks structural requirements for nerves, adapters, and connectors.
"""

import json
import os
import re
import sys

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


_schema_cache: dict[str, dict] = {}
_role_tuning_profiles: dict | None = None


def load_role_tuning_profiles() -> dict:
    global _role_tuning_profiles
    if _role_tuning_profiles is None:
        path = os.path.join(SCHEMAS_DIR, "role_tuning_profiles.json")
        with open(path) as f:
            _role_tuning_profiles = json.load(f).get("roles", {})
    return _role_tuning_profiles


def load_schema(name: str) -> dict:
    if name not in _schema_cache:
        path = os.path.join(SCHEMAS_DIR, name)
        with open(path) as f:
            _schema_cache[name] = json.load(f)
    return _schema_cache[name]


def load_json(path: str) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ERROR: Cannot parse {path}: {e}")
        return None


def validate_json_against_schema(data: dict | list, schema: dict, filepath: str) -> list[str]:
    """Basic schema validation without jsonschema dependency.

    Checks required fields, types, and enum constraints.
    Falls back gracefully if jsonschema is not installed.
    """
    errors = []
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
        for error in validator.iter_errors(data):
            errors.append(f"  {filepath}: {error.message} (at {'/'.join(str(p) for p in error.absolute_path)})")
        return errors
    except ImportError:
        pass

    # Fallback: manual validation of required fields and enums
    if schema.get("type") == "object" and isinstance(data, dict):
        for field in schema.get("required", []):
            if field not in data:
                errors.append(f"  {filepath}: missing required field '{field}'")
        for field, prop in schema.get("properties", {}).items():
            if field in data and "enum" in prop:
                if data[field] not in prop["enum"]:
                    errors.append(f"  {filepath}: '{field}' must be one of {prop['enum']}, got '{data[field]}'")
    elif schema.get("type") == "array" and isinstance(data, list):
        min_items = schema.get("minItems", 0)
        if len(data) < min_items:
            errors.append(f"  {filepath}: array must have at least {min_items} items, got {len(data)}")

    return errors


def check_tool_safety(filepath: str) -> list[str]:
    """Check a tool file for unsafe patterns based on its language."""
    errors = []
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except OSError:
        return errors

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".py":
        patterns = UNSAFE_PATTERNS_PYTHON
    elif ext in (".js", ".ts", ".mjs"):
        patterns = UNSAFE_PATTERNS_JS
    else:
        return errors

    for pattern, name in patterns:
        if re.search(pattern, content):
            errors.append(f"  UNSAFE: {filepath} contains {name}")
    return errors


def validate_nerve(nerve_dir: str) -> list[str]:
    """Validate a nerve bundle directory."""
    errors = []
    name = os.path.basename(nerve_dir)

    # bundle.json must exist
    bundle_path = os.path.join(nerve_dir, "bundle.json")
    if not os.path.exists(bundle_path):
        errors.append(f"  {name}: missing bundle.json")
        return errors

    bundle = load_json(bundle_path)
    if bundle is None:
        return errors

    schema = load_schema("bundle.schema.json")
    errors.extend(validate_json_against_schema(bundle, schema, bundle_path))

    # test_cases.json must exist with >= 4 cases
    tests_path = os.path.join(nerve_dir, "test_cases.json")
    if not os.path.exists(tests_path):
        errors.append(f"  {name}: missing test_cases.json")
    else:
        tests = load_json(tests_path)
        if tests is not None:
            test_schema = load_schema("test_cases.schema.json")
            errors.extend(validate_json_against_schema(tests, test_schema, tests_path))
            # Check for core and negative tests
            types = [t.get("type") for t in tests if isinstance(t, dict)]
            if "core" not in types:
                errors.append(f"  {name}: test_cases.json must have at least 1 'core' test")
            if "negative" not in types:
                errors.append(f"  {name}: test_cases.json must have at least 1 'negative' test")

    # Validate tools
    for tool in bundle.get("tools", []):
        tool_name = tool.get("name", "")
        spec_path = os.path.join(nerve_dir, tool.get("spec", ""))
        if not os.path.exists(spec_path):
            errors.append(f"  {name}: tool '{tool_name}' missing spec at {tool.get('spec', '')}")
        else:
            spec = load_json(spec_path)
            if spec is not None:
                spec_schema = load_schema("tool_spec.schema.json")
                errors.extend(validate_json_against_schema(spec, spec_schema, spec_path))

        # Check implementations (any language)
        for lang, impl_path in tool.get("implementations", {}).items():
            full_path = os.path.join(nerve_dir, impl_path)
            if not os.path.exists(full_path):
                errors.append(f"  {name}: tool '{tool_name}' missing {lang} implementation at {impl_path}")
            else:
                errors.extend(check_tool_safety(full_path))

    return errors


def validate_adapter(adapter_dir: str) -> list[str]:
    """Validate a brain adapter directory."""
    errors = []
    name = os.path.basename(adapter_dir)

    # Required files
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

    # Optional: qualification.json (generated by running system, not by contributors)
    qual_schema_path = os.path.join(adapter_dir, "qualification.json")
    if os.path.exists(qual_schema_path):
        data = load_json(qual_schema_path)
        if data is not None:
            schema = load_schema("adapter_qualification.schema.json")
            errors.extend(validate_json_against_schema(data, schema, qual_schema_path))

    # Check score range in qualification
    qual_path = os.path.join(adapter_dir, "qualification.json")
    if os.path.exists(qual_path):
        qual = load_json(qual_path)
        if qual and isinstance(qual, dict):
            score = qual.get("overall_score", -1)
            if not (0.0 <= score <= 1.0):
                errors.append(f"  {name}: qualification score must be 0.0-1.0, got {score}")

    # Check size_class validity
    meta_path = os.path.join(adapter_dir, "meta.json")
    if os.path.exists(meta_path):
        meta = load_json(meta_path)
        if meta and isinstance(meta, dict):
            sc = meta.get("size_class", "")
            if sc and sc not in ("tinylm", "small", "medium", "large"):
                errors.append(f"  {name}: invalid size_class '{sc}'")

    # Validate tuning target_modules against role profile
    if os.path.exists(meta_path):
        meta = meta if meta else load_json(meta_path)
        if meta and isinstance(meta, dict):
            # Derive role from directory structure: adapters/{role}/{size_class}
            role = os.path.basename(os.path.dirname(adapter_dir))
            profiles = load_role_tuning_profiles()
            profile = profiles.get(role)
            tuning = meta.get("tuning", {})
            if profile and tuning:
                # Validate lora_target_modules
                target_modules = tuning.get("lora_target_modules", [])
                allowed = set(profile.get("allowed_target_modules", []))
                for mod in target_modules:
                    if mod not in allowed:
                        errors.append(
                            f"  {name}: lora_target_module '{mod}' not allowed for role '{role}'. "
                            f"Allowed: {sorted(allowed)}"
                        )
                # Validate lora_rank
                rank = tuning.get("lora_rank", 0)
                max_rank = profile.get("max_lora_rank", 999)
                if rank > max_rank:
                    errors.append(
                        f"  {name}: lora_rank {rank} exceeds max {max_rank} for role '{role}'"
                    )

    return errors


def validate_tool(tool_dir: str) -> list[str]:
    """Validate a community tool directory."""
    errors = []
    name = os.path.basename(tool_dir)

    # meta.json must exist and validate against schema
    meta_path = os.path.join(tool_dir, "meta.json")
    if not os.path.exists(meta_path):
        errors.append(f"  {name}: missing meta.json")
    else:
        meta = load_json(meta_path)
        if meta is not None:
            schema = load_schema("tool_meta.schema.json")
            errors.extend(validate_json_against_schema(meta, schema, meta_path))

    # Implementation files listed in meta.json must exist and be safe
    meta = load_json(meta_path) if os.path.exists(meta_path) else None
    implementations = meta.get("implementations", {}) if meta else {}
    if not implementations:
        errors.append(f"  {name}: no implementations listed in meta.json")
    for lang, impl_file in implementations.items():
        impl_path = os.path.join(tool_dir, impl_file)
        if not os.path.exists(impl_path):
            errors.append(f"  {name}: missing {lang} implementation: {impl_file}")
        else:
            errors.extend(check_tool_safety(impl_path))

    # tests.json must exist and validate
    tests_path = os.path.join(tool_dir, "tests.json")
    if not os.path.exists(tests_path):
        errors.append(f"  {name}: missing tests.json")
    else:
        tests = load_json(tests_path)
        if tests is not None:
            tests_schema = load_schema("tool_tests.schema.json")
            errors.extend(validate_json_against_schema(tests, tests_schema, tests_path))

    # README.md must exist
    readme_path = os.path.join(tool_dir, "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"  {name}: missing README.md")

    return errors


def validate_mcp(mcp_dir: str) -> list[str]:
    """Validate an external MCP server directory."""
    errors = []
    name = os.path.basename(mcp_dir)

    # meta.json must exist and validate against schema
    meta_path = os.path.join(mcp_dir, "meta.json")
    if not os.path.exists(meta_path):
        errors.append(f"  {name}: missing meta.json")
    else:
        meta = load_json(meta_path)
        if meta is not None:
            schema = load_schema("mcp_meta.schema.json")
            errors.extend(validate_json_against_schema(meta, schema, meta_path))

    # README.md must exist
    readme_path = os.path.join(mcp_dir, "README.md")
    if not os.path.exists(readme_path):
        errors.append(f"  {name}: missing README.md")

    return errors


def validate_connector(connector_dir: str) -> list[str]:
    """Validate a connector directory."""
    errors = []
    name = os.path.basename(connector_dir)

    # Required files
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

    # Must have at least one implementation file
    has_impl = any(
        f.startswith("connector.") for f in os.listdir(connector_dir) if os.path.isfile(os.path.join(connector_dir, f))
    )
    if not has_impl:
        errors.append(f"  {name}: missing connector implementation (connector.js or connector.py)")

    return errors


def main():
    errors = []

    # Validate all nerves
    nerves_dir = os.path.join(REPO_ROOT, "nerves")
    if os.path.isdir(nerves_dir):
        for name in sorted(os.listdir(nerves_dir)):
            nerve_dir = os.path.join(nerves_dir, name)
            if os.path.isdir(nerve_dir):
                print(f"Validating nerve: {name}")
                errors.extend(validate_nerve(nerve_dir))

    # Validate all adapters (across all roles, size classes, and model-specific)
    # Structure: adapters/{role}/{size_class}/[context.json, meta.json]
    #            adapters/{role}/{size_class}/{model_name}/[context.json, meta.json]
    adapters_root = os.path.join(REPO_ROOT, "adapters")
    if os.path.isdir(adapters_root):
        for role in sorted(os.listdir(adapters_root)):
            role_dir = os.path.join(adapters_root, role)
            if not os.path.isdir(role_dir):
                continue
            for size_class in sorted(os.listdir(role_dir)):
                size_dir = os.path.join(role_dir, size_class)
                if not os.path.isdir(size_dir):
                    continue
                # Validate the size-class level adapter
                print(f"Validating adapter: {role}/{size_class}")
                errors.extend(validate_adapter(size_dir))
                # Validate model-specific adapters within this size class
                for model_name in sorted(os.listdir(size_dir)):
                    model_dir = os.path.join(size_dir, model_name)
                    if os.path.isdir(model_dir):
                        print(f"Validating adapter: {role}/{size_class}/{model_name}")
                        errors.extend(validate_adapter(model_dir))

    # Validate all connectors
    connectors_dir = os.path.join(REPO_ROOT, "connectors")
    if os.path.isdir(connectors_dir):
        for name in sorted(os.listdir(connectors_dir)):
            connector_dir = os.path.join(connectors_dir, name)
            if os.path.isdir(connector_dir):
                print(f"Validating connector: {name}")
                errors.extend(validate_connector(connector_dir))

    # Validate all tools
    tools_dir = os.path.join(REPO_ROOT, "tools")
    if os.path.isdir(tools_dir):
        for name in sorted(os.listdir(tools_dir)):
            tool_dir = os.path.join(tools_dir, name)
            if os.path.isdir(tool_dir):
                print(f"Validating tool: {name}")
                errors.extend(validate_tool(tool_dir))

    # Validate all external MCPs
    mcps_dir = os.path.join(REPO_ROOT, "mcps")
    if os.path.isdir(mcps_dir):
        for name in sorted(os.listdir(mcps_dir)):
            mcp_dir = os.path.join(mcps_dir, name)
            if os.path.isdir(mcp_dir):
                print(f"Validating mcp: {name}")
                errors.extend(validate_mcp(mcp_dir))

    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\nAll validations passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
