## Adapter Contribution

**Role**: <!-- brain | code | creative | awareness | communication | nerve | vision -->
**Size Class**: <!-- tinylm | small | medium | large -->
**Model Name**: <!-- e.g., llama3.2-3b -->
**Qualification Score**: <!-- e.g., 0.88 -->

### Checklist

#### Content Quality
- [ ] `system_prompt` in `context.json` is a plain text string (no embedded JSON objects or dicts)
- [ ] Prompts are generic and community-appropriate (no references to specific bots or products)
- [ ] `description` in `meta.json` clearly explains what the adapter does
- [ ] System prompts do not reference tool names — tools are declared separately, not in the prompt

#### Completeness
- [ ] `context.json`, `meta.json`, and `test_bank.jsonl` are all present
- [ ] Test bank covers core, edge, boundary, and negative categories
- [ ] Only model-specific path modified (`adapters/{role}/{size}/{model}/`) — not default adapter files

#### General
- [ ] No hardcoded secrets, tokens, API keys, or absolute paths
- [ ] Qualification score meets minimum threshold (0.7)
- [ ] No score regression against main branch
