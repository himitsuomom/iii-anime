# iii Skills

Top-level skills for building on the [iii engine](https://iii.dev). This catalog stays compact on
purpose; worker-backed capability skills live with their worker docs and `workers.iii.dev`.

## Install

```bash
npx skills add iii-hq/iii/skills
```

## Catalog

- [iii-getting-started](iii-getting-started/SKILL.md) — Install iii, create a project, write your first worker, and add registry workers
- [iii-core-primitives](iii-core-primitives/SKILL.md) — Functions, triggers, workers, registry access, invocation modes, trigger schemas, custom triggers, channels, and HTTP-invoked functions
- [iii-sdk-reference](iii-sdk-reference/SKILL.md) — Node.js, browser, Python, and Rust SDK usage in one place
- [iii-engine-config](iii-engine-config/SKILL.md) — Configure ports, workers, adapters, queues, RBAC, and observability
- [iii-architecture-patterns](iii-architecture-patterns/SKILL.md) — Workflows, reactive backends, agentic pipelines, CQRS, effect pipelines, and automation chains
- [iii-error-handling](iii-error-handling/SKILL.md) — Engine and SDK errors, retryability, RBAC denial, and timeout handling

### Agent infrastructure

Native iii worker patterns ported from the `自動コード生成` starred list (see [INTEGRATIONS.md](../INTEGRATIONS.md)).

- [iii-agent-memory](iii-agent-memory/SKILL.md) — Long-term memory + context engine worker with auto-capture triggers
- [iii-agent-observability](iii-agent-observability/SKILL.md) — LLM/agent tracing and an `llm-eval` evaluation worker
- [iii-doc-ingestion](iii-doc-ingestion/SKILL.md) — Document → markdown conversion, chunking, and RAG ingestion worker
- [iii-code-graph](iii-code-graph/SKILL.md) — Code knowledge graph worker with commit auto-sync
- [iii-multi-agent-orchestration](iii-multi-agent-orchestration/SKILL.md) — Role-based agent teams, swarms, fan-out/fan-in, shared state
- [iii-agent-harness](iii-agent-harness/SKILL.md) — Plan → work → review loop as iii functions and triggers
- [iii-file-search](iii-file-search/SKILL.md) — Fast fuzzy file/content/symbol search worker for agents
- [iii-agent-routing](iii-agent-routing/SKILL.md) — LLM gateway/router worker with cost-aware provider failover
