# Contributing to Arqitect Community

## What Can Be Contributed

The community accepts contributions in five categories:

| Type | Directory | Description |
|------|-----------|-------------|
| **Nerves** | `nerves/` | Specialized AI agents with system prompts, few-shot examples, and optional tools |
| **Adapters** | `adapters/{role}/{size}/{model}/` | Model-specific configurations for roles (brain, code, creative, etc.) |
| **MCP Tools** | `mcp_tools/` | Python/Go/Node functions that nerves can discover and use at runtime |
| **External MCP Servers** | `mcps/` | References to pre-built MCP server packages (npm, GitHub) |
| **Connectors** | `connectors/` | Platform integrations (WhatsApp, Telegram, Discord, Slack, etc.) |

---

## Submitting a Nerve

Nerves are specialized AI agents. Each nerve has a system prompt, few-shot examples, and optional MCP tool bindings, packaged across multiple model size classes.

### Structure

```
nerves/{name}/
├── bundle.json                # Nerve identity, role, tags, tools, authors
├── test_cases.json            # Test cases (core, edge, boundary, negative)
├── large/
│   ├── context.json           # System prompt, few-shot examples, temperature, qualification_score
│   └── meta.json              # Model config, tuning params, qualification thresholds
├── medium/
│   ├── context.json
│   ├── meta.json
│   └── {model_name}/          # Optional model-specific overrides
│       ├── context.json
│       └── meta.json
├── small/
│   ├── context.json
│   └── meta.json
└── tinylm/
    ├── context.json
    └── meta.json
```

### Requirements

- **System prompts must be plain text** — the `system_prompt` field in `context.json` must be a plain text string. Do not embed JSON objects, dicts, or structured data inside the string. No `{ "system": "..." }` wrappers.
- **Prompts must be generic and community-appropriate** — do not reference specific bots, products, or proprietary systems (e.g., "my-bot", "our-app"). The nerve should work for any user.
- **No vendor-specific tool dependencies** — system prompts must not instruct the nerve to "always use" a vendor-specific tool (e.g., "Always use SearchWixCLIDocumentation for database comparisons"). Vendor-specific tools may be listed as available, but the nerve's core behavior must not depend on them.
- **Do not reference tools in system prompts** — tools are declared in `bundle.json`, not in the system prompt. The system prompt should describe the nerve's behavior and expertise, not list or reference specific tool names. Tool routing is handled by the runtime.
- **Descriptions must be meaningful** — the `description` field in `bundle.json` and `meta.json` should clearly explain what the nerve does, not just repeat the nerve name.
- **All declared tools must be included** — every tool listed in `bundle.json` must have its implementation file (`tool.py`, `tool.go`, etc.) present in the PR under `mcp_tools/`.
- **No dead imports or unreachable code** in tool implementations.
- **Test cases required** — `test_cases.json` must include core, edge, boundary, and negative categories. No duplicate test entries.
- **Qualification score** — must meet the `minimum_threshold` defined in `meta.json` (typically 0.7). Score regressions against `main` are rejected automatically by CI.
- **No secrets** — no API keys, tokens, passwords, or private keys in any file.
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`.
- **One PR per nerve** — do not submit multiple PRs for the same nerve. If a duplicate exists, only the one with the highest qualification score will be kept.

### MCP Tools in Nerves

If your nerve declares tools in `bundle.json`:

- Each tool must have a working implementation file included in the PR.
- If a tool requires an API key or secret to function, the tool must accept it via its constructor or configuration — never hardcode secrets.
- Tool code must not use unsafe calls (`eval`, `exec`, `subprocess`, `os.system`).
- Remove unused imports — no dead code.

---

## Submitting an Adapter

Adapters are model-specific configurations for roles like `brain`, `code`, `creative`, `awareness`, `communication`, `nerve`, and `vision`.

Community PRs can only add **model-specific** adapters under `adapters/{role}/{size_class}/{model_name}/`. Default adapters (directly under the size class) are managed by the core team.

### Structure

```
adapters/{role}/{size_class}/{model_name}/
├── context.json       # System prompt, few-shot examples, temperature, qualification_score
├── meta.json          # Model config, tuning params, qualification thresholds
└── test_bank.jsonl    # Test cases (one JSON object per line)
```

### Requirements

- **System prompts must be plain text** — same rules as nerves.
- **Prompts must be generic** — no references to specific bots or products.
- **Do not reference tools in system prompts** — same rules as nerves.
- **Score must meet thresholds** — no regressions against `main`.
- **No secrets or absolute paths**.
- **Only model-specific paths** — do not modify default adapter files.

---

## Submitting a Tool

MCP tools are functions that arqitect-core can discover and install at runtime. When a nerve needs a capability, `acquire_tool()` checks the community manifest before fabricating from scratch.

### Structure

```
mcp_tools/{name}/
├── meta.json     # Name, version, description, category, tags, parameters, implementations
├── tool.py       # Python implementation (run() function with docstring)
├── tool.go       # Go implementation (optional — provide at least one language)
├── tool.js       # Node implementation (optional)
├── tests.json    # Test cases (min 2) — validates against schemas/tool_tests.schema.json
└── README.md     # Usage docs and examples
```

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file.
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`.
- **Schema valid** — `meta.json` must conform to `schemas/tool_meta.schema.json`.
- **Safe code** — no dangerous calls (`eval`, `exec`, `subprocess`, `os.system`).
- **Good description** — `description` and `tags` in `meta.json` are used for runtime matching. Be specific so `acquire_tool()` can find your tool.
- **README included** — usage docs for contributors and users.
- **`requires_api_key`** — set to `true` if the tool needs an external API key. If it does, the tool must accept the key via constructor or parameter — never hardcode it.
- **No dead imports** — remove unused imports and unreachable code.

### Example meta.json

```json
{
  "name": "currency_converter",
  "version": "1.0.0",
  "description": "Convert between currencies using live exchange rates",
  "implementations": {
    "python": "tool.py",
    "go": "tool.go"
  },
  "author": { "github": "your-username" },
  "category": "finance",
  "tags": ["currency", "exchange", "conversion", "money"],
  "parameters": [
    { "name": "amount", "type": "number", "description": "Amount to convert" },
    { "name": "from_currency", "type": "string", "description": "Source currency code (e.g., USD)" },
    { "name": "to_currency", "type": "string", "description": "Target currency code (e.g., EUR)" }
  ],
  "requires_api_key": false
}
```

---

## Submitting an External MCP Server

External MCP servers are pre-built packages (npm, GitHub) that arqitect-core can connect to at runtime.

### Structure

```
mcps/{name}/
├── meta.json     # Server metadata, command, auth, tools, capabilities
└── README.md     # Description and setup instructions
```

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file.
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`.
- **Schema valid** — `meta.json` must conform to `schemas/mcp_meta.schema.json`.
- **Good description** — `description` and `capabilities` are used for runtime matching.
- **README included** — setup instructions for users.
- **Working package** — the npm package or GitHub repo must be publicly accessible.

### Example meta.json

```json
{
  "name": "duckduckgo",
  "version": "1.0.0",
  "description": "DuckDuckGo search engine — web search and content fetching without API keys",
  "source": "npm",
  "package": "duckduckgo-mcp-server",
  "command": ["npx", "-y", "duckduckgo-mcp-server"],
  "auth_type": "none",
  "tools": ["search", "fetch_content"],
  "capabilities": ["web_search", "knowledge", "facts", "news", "lookup"],
  "category": "search"
}
```

---

## Submitting a Connector

Connectors are platform integrations (WhatsApp, Telegram, Discord, Slack, etc.).

### Structure

```
connectors/{name}/
├── meta.json              # Capabilities, config fields, redis channels
├── config-template.json   # Config structure (no real secrets)
├── README.md              # Setup and usage instructions
└── connector.{js,py,ts}   # Implementation
```

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file.
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`.
- **Schema valid** — `meta.json` must conform to `schemas/connector_meta.schema.json`.
- **Safe code** — no dangerous calls (`eval`, `exec`, `subprocess` in Python; `child_process`, `eval` in JS/TS).
- **README included** — setup instructions for users.

---

## PR Review Checklist

Every PR is reviewed against these criteria. PRs that fail will be asked to fix issues or closed.

### Content Quality
- [ ] System prompts are **plain text strings** — no embedded JSON objects or dicts
- [ ] Prompts are **generic and community-appropriate** — no references to specific bots, products, or vendors
- [ ] System prompts do **not hardcode vendor-specific tools** as the primary/default behavior
- [ ] System prompts do **not reference tool names** — tools belong in `bundle.json`, not in the prompt
- [ ] Descriptions are **meaningful** — not just the nerve/adapter name repeated

### Completeness
- [ ] All tools declared in `bundle.json` have their implementation files included
- [ ] Tool implementations have no dead imports or unreachable code
- [ ] Test cases cover core, edge, boundary, and negative categories
- [ ] No duplicate test entries

### Tools & Secrets
- [ ] Tools that require API keys accept them via constructor or parameter
- [ ] No hardcoded secrets, tokens, or API keys anywhere
- [ ] `requires_api_key` is set correctly in tool `meta.json`

### Score & Duplicates
- [ ] Qualification score meets `minimum_threshold` (typically 0.7)
- [ ] No score regression against `main`
- [ ] No duplicate PRs for the same nerve — only the highest score is kept

> **Auto-close policy**: PRs that introduce a score regression (any tier lower than `main`) or are duplicates of an existing open PR are **closed immediately without review**. No feedback is requested — fix the issue and open a new PR.

### Safety
- [ ] No unsafe calls (`eval`, `exec`, `subprocess`, `os.system`)
- [ ] No absolute paths
- [ ] No secrets or sensitive data

---

## CI Validation

All PRs are validated automatically by CI:

- **Path protection** — community PRs can only modify: `nerves/`, `adapters/{role}/{size}/{model}/`, `connectors/`, `mcp_tools/`, `mcps/`
- **JSON schema validation** against `schemas/`
- **Secret scanning**
- **Score quality checks** — below-threshold or regressing scores cause auto-close
- **Test suite** — all tests must pass
- **Auto-approve and auto-merge** — PRs that pass all checks are approved and merged automatically
