## Nerve Contribution

**Name**: <!-- e.g., science_nerve -->
**Role**: <!-- tool | creative | code | reasoning -->
**Qualification Score**: <!-- e.g., 0.93 -->

### What it does
<!-- Brief description of what this nerve specializes in -->

### Checklist

#### Content Quality
- [ ] `system_prompt` in all `context.json` files is a plain text string (no embedded JSON objects or dicts)
- [ ] Prompts are generic and community-appropriate (no references to specific bots, products, or proprietary systems)
- [ ] `description` in `bundle.json` and `meta.json` clearly explains what the nerve does (not just the nerve name)
- [ ] System prompts do not reference tool names — tools are declared in `bundle.json`, not in the prompt

#### Completeness
- [ ] All tools listed in `bundle.json` have their implementation files included in the PR
- [ ] `test_cases.json` includes core, edge, boundary, and negative test categories
- [ ] No duplicate test entries
- [ ] All size variants included (large, medium, small, tinylm)

#### Tools (if applicable)
- [ ] Tool implementations have no dead imports or unused code
- [ ] Tools that require API keys accept them via constructor or parameter (never hardcoded)
- [ ] No unsafe calls (`eval`, `exec`, `subprocess`, `os.system`)

#### General
- [ ] No hardcoded secrets, tokens, API keys, or absolute paths
- [ ] Qualification score meets minimum threshold (0.7)
- [ ] Qualification score is **not lower** than the current score on `main` for any tier
- [ ] No other open PR for the same nerve

> **Note**: PRs with a score regression (any tier lower than `main`) or duplicates of an existing open PR are closed immediately without review.
