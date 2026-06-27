# iii-harness — Claude Code plugin

A plan → work → review coding-agent harness for building on the [iii engine](https://iii.dev),
plus the iii agent-infrastructure skills. This plugin is the Claude Code surface of the
[`自動コード生成` integration](../INTEGRATIONS.md): it bundles the harness/plugin repos from that
starred list (compound-engineering-plugin, claude-code-harness, revfactory/harness, ECC,
cursor/plugins, knowledge-work-plugins) as a single installable unit, alongside the iii skills that
port the agent-infrastructure repos (MetaGPT, opik, supermemory, markitdown, codegraph, fff,
9router, …) into native iii workers.

## What's inside

| Kind | Name | Purpose |
| --- | --- | --- |
| Agent | `iii-planner` | Turns a request into a reviewable plan in iii primitives |
| Agent | `iii-implementer` | Executes an approved plan, keeps the build green |
| Agent | `iii-reviewer` | Adversarially verifies the diff, feeds lessons back |
| Command | `/iii-harness <task>` | Runs the full plan→work→review loop until review passes |
| Command | `/iii-compound [lesson]` | Captures a session lesson into `skills/` |
| Skills | `../skills` | The full iii skill catalog, including the new agent-infra skills |

## Install

This repo is a Claude Code plugin marketplace (see `.claude-plugin/marketplace.json` at the repo
root). Add the marketplace and install the plugin:

```
/plugin marketplace add iii-hq/iii
/plugin install iii-harness@iii
```

Or install just the skills without the plugin:

```bash
npx skills add iii-hq/iii/skills
```

## The loop

```
/iii-harness add a rate-limited llm-router worker with provider failover
   → iii-planner   produces the plan (workers, functions, triggers, checks)
   → iii-implementer  writes it, build stays green
   → iii-reviewer  PASS/FAIL with file:line findings; FAIL loops back
   → compound      reviewer's lesson lands in skills/ for next time
```

See [`skills/iii-agent-harness`](../skills/iii-agent-harness/SKILL.md) for the same loop modeled as
iii functions and triggers (running the harness *on* iii rather than in the editor).
