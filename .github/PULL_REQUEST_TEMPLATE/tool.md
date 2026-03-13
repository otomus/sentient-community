## Tool Contribution

**Name**: <!-- e.g., currency_converter -->
**Category**: <!-- e.g., finance, weather, entertainment, utilities -->
**Languages**: <!-- e.g., python, go, node -->

### What it does
<!-- Brief description of what this tool does and what APIs it uses -->

### Checklist
- [ ] `meta.json` validates against `schemas/tool_meta.schema.json`
- [ ] `implementations` in `meta.json` maps each language to its file (e.g., `"python": "tool.py"`)
- [ ] All listed implementation files exist and have a `run()` function with clear docstring
- [ ] `tests.json` with at least 2 test cases (validates against `schemas/tool_tests.schema.json`)
- [ ] `README.md` with usage examples included
- [ ] No hardcoded tokens, keys, or absolute paths
- [ ] No unsafe calls (`eval`, `exec`, `subprocess`, `os.system`)
- [ ] `requires_api_key` set correctly in `meta.json`
