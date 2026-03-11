# Sentient Community

Community hub for sharing connector implementations and discovering nerves and brain adapters for [Sentient](https://github.com/otomus/sentient).

## What's Here

| Directory | Contents | Description | Managed By |
|-----------|----------|-------------|------------|
| `connectors/` | Connectors | Full implementations for messaging platforms | Community PRs |
| `nerves/` | Nerve bundles | Identity + tools + test cases for autonomous agents | Sentient core |
| `adapters/brain/` | Brain adapters | Per-model system prompts, LoRA weights, qualification scores | Sentient core |

## Connectors — Community Contributions

Connectors are the only manually contributed content. They are full implementations for messaging platforms (WhatsApp, Telegram, Discord, Slack, etc.) submitted via PR.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit a connector.

### Requirements

- `meta.json`, `config-template.json` (no secrets), `README.md`, and an implementation file
- Schema valid, no secrets, no absolute paths

## Nerves and Adapters — System Managed

Nerves and brain adapters are **not manually contributed**. They are synthesized, qualified, and exported by sentient-core automatically.

When Sentient's brain synthesizes a nerve, it checks this repo for a matching bundle. If one exists, the proven identity (system prompt, examples, tools, test cases) is used instead of generating from scratch.

```bash
# Sync community content to your local cache
python cli.py community sync

# Search available nerves
python cli.py community search "weather"
```

## Validation

All PRs are validated by CI:
- JSON schema validation
- Secret scanning (API keys, private keys, absolute paths)
- Tool safety checks (no `eval`, `exec`, `os.system`, `subprocess` in Python; no `child_process`, `execSync` in JS/TS)
- Structural completeness

## Manifest

`manifest.json` is auto-generated on merge — an index of all nerves, adapters, and connectors for programmatic discovery.

## License

MIT License — see [LICENSE](LICENSE).
