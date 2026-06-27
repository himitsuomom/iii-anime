# Integrations — `自動コード生成` starred list

This document maps the [`自動コード生成` (Automatic Code Generation) GitHub stars
list](https://github.com/stars/himitsuomom/lists/%E8%87%AA%E5%8B%95%E3%82%B3%E3%83%BC%E3%83%89%E7%94%9F%E6%88%90/)
onto this repository. The agreed scope is **agent tooling + agent infrastructure**: the parts of the
list that can be meaningfully *installed and integrated* into iii.

The list mixes three kinds of project. They are integrated three different ways:

1. **Agent infrastructure** (memory, observability, doc conversion, code graphs, multi-agent,
   search, routing) → ported into native **iii worker patterns** as new skills under
   [`skills/`](skills/).
2. **Coding-agent harnesses, plugins, and skill packs** → bundled into the
   [`iii-harness` Claude Code plugin](claude-plugin/) (agents + slash commands) and the
   [`iii-agent-harness`](skills/iii-agent-harness/SKILL.md) skill.
3. **Out of scope** (a game engine, a web-app template, a stealth browser, learning resources) →
   not integrated; rationale recorded below so the decision is auditable.

Nothing here vendors external source. Each integration expresses the upstream capability in iii's
worker / function / trigger model, so it composes with the rest of the engine and is observable in
the console.

## Agent infrastructure → iii skills

| Starred repo | What it does upstream | Integrated as |
| --- | --- | --- |
| [supermemoryai/supermemory](https://github.com/supermemoryai/supermemory) | Memory + context engine, Memory API | [`iii-agent-memory`](skills/iii-agent-memory/SKILL.md) — `memory::add/search/get/forget` worker over state + embeddings, auto-capture triggers |
| [comet-ml/opik](https://github.com/comet-ml/opik) | LLM tracing, evaluation, dashboards | [`iii-agent-observability`](skills/iii-agent-observability/SKILL.md) — trace/span + token/cost/latency metadata, `llm-eval` worker, console wiring |
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | Files/office docs → Markdown | [`iii-doc-ingestion`](skills/iii-doc-ingestion/SKILL.md) — `doc::convert/chunk/ingest` Python worker for RAG |
| [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) · [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) | Pre-indexed / interactive code knowledge graph | [`iii-code-graph`](skills/iii-code-graph/SKILL.md) — `codegraph::index/query/sync/explain` worker, commit auto-sync trigger |
| [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) · [ruvnet/ruflo](https://github.com/ruvnet/ruflo) · [ogulcancelik/herdr](https://github.com/ogulcancelik/herdr) | Multi-agent framework / swarm meta-harness / agent multiplexer | [`iii-multi-agent-orchestration`](skills/iii-multi-agent-orchestration/SKILL.md) — role workers, swarms, fan-out/fan-in, blackboard state |
| [dmtrKovalenko/fff](https://github.com/dmtrKovalenko/fff) | File search SDK for AI agents | [`iii-file-search`](skills/iii-file-search/SKILL.md) — `search::files/content/symbols` worker |
| [decolua/9router](https://github.com/decolua/9router) · [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) | Multi-provider AI routing / terminal coding agent | [`iii-agent-routing`](skills/iii-agent-routing/SKILL.md) — `llm::complete/chat/embed` gateway with cost-aware failover |

## Harnesses, plugins, skill packs → `iii-harness` plugin + skill

| Starred repo | What it does upstream | Integrated as |
| --- | --- | --- |
| [Chachamaru127/claude-code-harness](https://github.com/Chachamaru127/claude-code-harness) | Plan-work-review cycle | [`iii-harness` plugin](claude-plugin/) agents (`iii-planner`/`iii-implementer`/`iii-reviewer`) + `/iii-harness`; modeled on iii in [`iii-agent-harness`](skills/iii-agent-harness/SKILL.md) |
| [revfactory/harness](https://github.com/revfactory/harness) | Meta-skill for designing agent teams | Role-agent design in the plugin + orchestration skill |
| [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) | Compound-engineering plugin | `/iii-compound` command + reviewer's write-back-to-`skills/` loop |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | Harness performance optimization | Iteration/retry budget + observability in `iii-agent-harness` |
| [cursor/plugins](https://github.com/cursor/plugins) · [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | Plugin specs / knowledge-work plugins | Packaged as a Claude Code plugin + marketplace (`.claude-plugin/marketplace.json`) |
| [mattpocock/skills](https://github.com/mattpocock/skills) · [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | Engineering skill collections | Skill-as-folder convention reused for the new `skills/` entries; installable via `npx skills add` |
| [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) | Cybersecurity skill pack | Out of catalog scope (security-domain pack); install separately via `npx skills add` — left as a follow-up rather than vendored |
| [iii-hq/iii](https://github.com/iii-hq/iii) | This repository | The integration target itself |

## Install

```bash
# iii skills (includes the new agent-infrastructure skills)
npx skills add iii-hq/iii/skills

# Claude Code harness plugin
/plugin marketplace add iii-hq/iii
/plugin install iii-harness@iii
```

## Out of scope (and why)

These are starred for reference but are not integrable into the iii engine without building an
unrelated product; integrating them would add large, low-value surface area.

| Starred repo | Why not integrated |
| --- | --- |
| [godotengine/godot](https://github.com/godotengine/godot) | A 2D/3D game engine — unrelated to a service-composition runtime. |
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | A standalone web-app scaffold; iii has its own project/worker scaffolding. |
| [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop) | A desktop GUI agent stack; an iii worker could *call* it, but it is not a library to embed. |
| [CloakHQ/CloakBrowser](https://github.com/CloakHQ/CloakBrowser) | A stealth browser; usable behind a worker but out of scope for a core integration. |
| [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) | A web UI for a specific agent; not a reusable capability. |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | A design-language doc, not installable software. |
| [rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch) | A learning resource, not a dependency. |
| [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) | Policy/sandbox governance — a strong future fit for an iii governance worker, deferred as a follow-up rather than stubbed now. |

> If you want any of the out-of-scope items wrapped as an iii worker (e.g. a CloakBrowser worker, a
> UI-TARS worker, or an agent-governance worker), that is a clean follow-up — open an issue and it
> can be added the same way as the skills above.
