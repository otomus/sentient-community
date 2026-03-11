# Contributing to Sentient Community

## What Can Be Contributed

**Connectors** are the only community-contributed content. Nerves, brain adapters, and all other sentient-core components are managed automatically by the system — they are not manually authored or submitted.

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

## Nerves and Adapters

Nerves and brain adapters in this repo are **managed by sentient-core**. They are synthesized, qualified, and exported by the system automatically. Do not submit PRs for nerves or adapters — they will be rejected.

## CI Validation

All PRs are validated automatically:
- JSON schema validation against `schemas/`
- Secret scanning
- Tool safety checks
- Structural completeness
