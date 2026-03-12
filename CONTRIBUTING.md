# Contributing to Sentient Community

## What Can Be Contributed

**Connectors**, **MCP Tools**, and **External MCP Servers** are community-contributed content. Nerves, brain adapters, and all other sentient-core components are managed automatically by the system — they are not manually authored or submitted.

## Submitting a Connector

Connectors (WhatsApp, Telegram, Discord, Slack, etc.) are full implementations submitted manually via PR.

### Structure

```
connectors/{name}/
├── meta.json              # Capabilities, config fields, redis channels
├── config-template.json   # Config structure (no real secrets)
├── README.md              # Setup and usage instructions
└── connector.{js,py,ts}   # Implementation
```

### Steps

1. Create your connector directory under `connectors/`
2. Add `meta.json` following `schemas/connector_meta.schema.json`
3. Add `config-template.json` with placeholder values (never real secrets)
4. Add a `README.md` with setup instructions
5. Add your implementation file
6. Open a PR using the connector PR template

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`
- **Schema valid** — `meta.json` must conform to `schemas/connector_meta.schema.json`
- **Safe code** — no dangerous calls (`eval`, `exec`, `subprocess` in Python; `child_process`, `eval` in JS/TS)
- **README included** — setup instructions for users

## Submitting a Tool

MCP tools are Python functions that sentient-core can discover and install at runtime. When a nerve needs a capability, `acquire_tool()` checks the community manifest before fabricating from scratch.

### Structure

```
tools/{name}/
├── meta.json     # Name, version, description, category, tags, parameters, implementations
├── tool.py       # Python implementation (run() function with docstring)
├── tool.go       # Go implementation (optional — provide at least one language)
├── tool.js       # Node implementation (optional)
├── tests.json    # Test cases (min 2) — validates against schemas/tool_tests.schema.json
└── README.md     # Usage docs and examples
```

Each tool must have at least one implementation. You can provide multiple — the MCP server loads the one matching its runtime (Python, Go, Node, Java, Rust).

### Steps

1. Create your tool directory under `tools/`
2. Add `meta.json` following `schemas/tool_meta.schema.json`
3. Add `tool.py` with a `run()` function and a clear docstring
4. Add `tests.json` with at least 2 test cases (see `schemas/tool_tests.schema.json`)
5. Add a `README.md` with usage examples
6. Open a PR using the tool PR template

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`
- **Schema valid** — `meta.json` must conform to `schemas/tool_meta.schema.json`
- **Safe code** — no dangerous calls (`eval`, `exec`, `subprocess`, `os.system`)
- **Good description** — `description` and `tags` in `meta.json` are used for runtime matching. Be specific so `acquire_tool()` can find your tool.
- **README included** — usage docs for contributors and users
- **`requires_api_key`** — set to `true` if the tool needs an external API key

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

## Submitting an External MCP Server

External MCP servers are pre-built packages (npm, GitHub) that sentient-core can connect to at runtime. Unlike tools, these are not local implementations — they are references to existing MCP servers that get launched as child processes.

### Structure

```
mcps/{name}/
├── meta.json     # Server metadata, command, auth, tools, capabilities
└── README.md     # Description and setup instructions
```

### Steps

1. Create your MCP directory under `mcps/`
2. Add `meta.json` following `schemas/mcp_meta.schema.json`
3. Add a `README.md` with setup instructions
4. Open a PR using the mcp PR template

### Requirements

- **No secrets** — no API keys, tokens, passwords, or private keys in any file
- **No absolute paths** — no `/Users/`, `/home/`, `C:\Users\`
- **Schema valid** — `meta.json` must conform to `schemas/mcp_meta.schema.json`
- **Good description** — `description` and `capabilities` are used for runtime matching
- **README included** — setup instructions for users
- **Working package** — the npm package or GitHub repo must be publicly accessible

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

## Nerves and Adapters

Nerves and brain adapters in this repo are **managed by sentient-core**. They are synthesized, qualified, and exported by the system automatically. Do not submit PRs for nerves or adapters — they will be rejected.

## CI Validation

All PRs are validated automatically:
- JSON schema validation against `schemas/`
- Secret scanning
- Tool safety checks
- Structural completeness
