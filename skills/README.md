# iii Skills

Top-level skills for building with the [iii engine](https://github.com/iii-hq/iii). The catalog is
intentionally small: it teaches the iii mental model, worker creation and registry access, SDK
usage, engine config, architecture patterns, and error handling. Worker-backed capability skills
stay with the worker docs and [workers.iii.dev](https://workers.iii.dev/) instead of duplicating
queue, pub/sub, state, cron, stream, or observability here.

## Install

```bash
npx skills add iii-hq/iii/skills
```

### Install a single skill

```bash
npx skills add iii-hq/iii/skills --skill iii-core-primitives
```

## Skills

| Skill                                                  | What it does |
| ------------------------------------------------------ | ------------ |
| [iii-getting-started](./iii-getting-started)           | Install iii, create a project, write your first worker, and add registry workers |
| [iii-core-primitives](./iii-core-primitives)           | Functions, triggers, workers, registry access, invocation modes, trigger schemas, custom triggers, channels, and HTTP-invoked functions |
| [iii-sdk-reference](./iii-sdk-reference)               | Node.js, browser, Python, and Rust SDK usage in one place |
| [iii-engine-config](./iii-engine-config)               | Configure ports, workers, adapters, queues, worker manager, RBAC, and observability |
| [iii-architecture-patterns](./iii-architecture-patterns) | Workflows, reactive backends, agentic pipelines, CQRS, effect pipelines, and automation chains |
| [iii-error-handling](./iii-error-handling)             | Engine and SDK errors, retryability, RBAC denial, and timeout handling |

### Agent infrastructure skills

These port the agent / automatic-code-generation tooling from the
[`自動コード生成` starred list](../INTEGRATIONS.md) into native iii worker patterns.

| Skill                                                  | What it does | Inspired by |
| ------------------------------------------------------ | ------------ | ----------- |
| [iii-agent-memory](./iii-agent-memory)                 | Long-term memory + context engine worker (`memory::add/search/get/forget`) over state and embeddings, with auto-capture triggers | supermemory |
| [iii-agent-observability](./iii-agent-observability)   | LLM/agent tracing, token/cost/latency spans, and an `llm-eval` worker (`eval::score/hallucination/relevance`) wired to iii observability | opik |
| [iii-doc-ingestion](./iii-doc-ingestion)               | Document → markdown conversion + chunk + ingest worker (`doc::convert/chunk/ingest`) for RAG | markitdown |
| [iii-code-graph](./iii-code-graph)                     | Code knowledge graph worker (`codegraph::index/query/sync/explain`) with commit auto-sync | codegraph, Understand-Anything |
| [iii-multi-agent-orchestration](./iii-multi-agent-orchestration) | Role-based agent teams, swarms, fan-out/fan-in, handoff, and shared blackboard state | MetaGPT, ruflo, herdr |
| [iii-agent-harness](./iii-agent-harness)               | Plan → work → review loop as iii functions with a gated task state machine and compound write-back | claude-code-harness, harness, compound-engineering, ECC |
| [iii-file-search](./iii-file-search)                   | Fast fuzzy file / content / symbol search worker for agents (`search::files/content/symbols`) | fff |
| [iii-agent-routing](./iii-agent-routing)               | LLM gateway/router worker (`llm::complete/chat/embed`) with cost-aware provider failover | 9router, oh-my-pi |

## Shape

Each skill is one folder with one `SKILL.md`. Code examples live directly in the skill, including
TypeScript, Python, and Rust examples where the concept is language-specific.

```text
skills/
├── iii-core-primitives/
│   └── SKILL.md
├── iii-sdk-reference/
│   └── SKILL.md
└── README.md
```

## Contributing

1. Fork this repo
2. Add or edit a top-level skill in `skills/`
3. Keep worker-specific capability skills with the worker docs
4. Submit a PR

## License

Apache-2.0
