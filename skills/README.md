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

### Install as a Claude Code plugin

These skills are also published as a Claude Code plugin via the marketplace
manifest at [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json).
Add the marketplace and install the plugin from inside Claude Code:

```text
/plugin marketplace add iii-hq/iii
/plugin install iii-skills@iii-skills
```

Claude Code then auto-discovers every `SKILL.md` under `skills/` and loads the
matching skill on demand.

## Skills

| Skill                                                  | What it does |
| ------------------------------------------------------ | ------------ |
| [iii-getting-started](./iii-getting-started)           | Install iii, create a project, write your first worker, and add registry workers |
| [iii-core-primitives](./iii-core-primitives)           | Functions, triggers, workers, registry access, invocation modes, trigger schemas, custom triggers, channels, and HTTP-invoked functions |
| [iii-sdk-reference](./iii-sdk-reference)               | Node.js, browser, Python, and Rust SDK usage in one place |
| [iii-engine-config](./iii-engine-config)               | Configure ports, workers, adapters, queues, worker manager, RBAC, and observability |
| [iii-architecture-patterns](./iii-architecture-patterns) | Workflows, reactive backends, agentic pipelines, CQRS, effect pipelines, and automation chains |
| [iii-error-handling](./iii-error-handling)             | Engine and SDK errors, retryability, RBAC denial, and timeout handling |

### Cybersecurity skills

This catalog also bundles **754 cybersecurity skills** (adapted from the
[Anthropic Cybersecurity Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
package, Apache-2.0) covering 26 security domains — cloud security, threat
hunting, threat intelligence, web app security, DFIR, malware analysis, red
teaming, and more. Each lives in its own `skills/<skill-name>/` folder with a
`SKILL.md`, plus `references/` and `scripts/`, and is auto-discovered by Claude
Code alongside the iii skills above. Browse them under
[`skills/`](.) — every directory whose name is not prefixed with `iii-` is a
cybersecurity skill.

## Index & framework mappings

- [`index.json`](./index.json) — a flat catalog of every skill (name,
  description, domain, path) so agents and tools can list all 760 skills in one
  read instead of opening each `SKILL.md`. Regenerate it after adding or editing
  a skill:

  ```bash
  python scripts/generate-skills-index.py
  ```

- [`mappings/`](./mappings) — coverage of the cybersecurity skills against
  industry frameworks: [MITRE ATT&CK](./mappings/mitre-attack) (plus an
  [ATT&CK Navigator layer](./mappings/attack-navigator-layer.json) you can load
  at <https://mitre-attack.github.io/attack-navigator/>),
  [NIST CSF](./mappings/nist-csf), and [OWASP](./mappings/owasp). These describe
  the bundled cybersecurity skills only.

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
