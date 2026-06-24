# iii Skills

Top-level skills for building on the [iii engine](https://iii.dev). This catalog stays compact on
purpose; worker-backed capability skills live with their worker docs and `workers.iii.dev`.

## Install

```bash
npx skills add iii-hq/iii/skills
```

Or install as a Claude Code plugin:

```text
/plugin marketplace add iii-hq/iii
/plugin install iii-skills@iii-skills
```

## Catalog

- [iii-getting-started](iii-getting-started/SKILL.md) — Install iii, create a project, write your first worker, and add registry workers
- [iii-core-primitives](iii-core-primitives/SKILL.md) — Functions, triggers, workers, registry access, invocation modes, trigger schemas, custom triggers, channels, and HTTP-invoked functions
- [iii-sdk-reference](iii-sdk-reference/SKILL.md) — Node.js, browser, Python, and Rust SDK usage in one place
- [iii-engine-config](iii-engine-config/SKILL.md) — Configure ports, workers, adapters, queues, RBAC, and observability
- [iii-architecture-patterns](iii-architecture-patterns/SKILL.md) — Workflows, reactive backends, agentic pipelines, CQRS, effect pipelines, and automation chains
- [iii-error-handling](iii-error-handling/SKILL.md) — Engine and SDK errors, retryability, RBAC denial, and timeout handling

Plus **754 bundled cybersecurity skills** (Apache-2.0, adapted from
[Anthropic Cybersecurity Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills))
across 26 security domains. Every `skills/` directory not prefixed with `iii-`
is one such skill; all are auto-discovered alongside the iii skills above.
