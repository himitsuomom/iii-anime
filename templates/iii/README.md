# iii template store

A scaffolding template store for iii. It holds **two kinds** of templates, both
discoverable through the same intent-based orchestrator:

1. **Compose stacks** — ready-to-run multi-service Docker Compose stacks adapted
   from Docker's [awesome-compose](https://github.com/docker/awesome-compose).
   Each requires Docker (`conditions.requires_docker: true`).
2. **Reference / knowledge packs** — curated "awesome-list" repos (e.g.
   `awesome-python`, `awesome-go`, `awesome-selfhosted`) imported as docs-only
   templates. Each scaffolds a `RESOURCES.md` (the curated list, with
   attribution) plus a structured `index.yaml` (the categories it covers), and
   is tagged `kind:reference` (`requires_docker: false`).

The layout mirrors what the iii scaffolder expects from a remote templates repo
(`<repo>/iii/template.yaml` plus one folder per template), so this directory can
be used directly as a local template source.

## Use a template

```bash
# List/select interactively, or pass --template <name>
iii project init my-stack --template fastapi --template-dir templates/iii

cd my-stack
docker compose up
```

`--template-dir templates/iii` points the scaffolder at this directory instead
of the default remote templates repo. Drop the flag (and set `III_TEMPLATE_URL`)
once these templates are published to a templates repo.

## Pick a template by intent (orchestration)

Instead of knowing the template name up front, describe what you want and let
the orchestrator choose the best fit:

```bash
iii project init my-api \
  --intent "a Go REST API with a postgres database" \
  --template-dir templates/iii
# → Matched template: Go / NGINX / PostgreSQL
```

The orchestrator scores every template's **selection metadata** (below) against
your intent. When one template clearly wins it is auto-selected; when several
fit, it presents a ranked shortlist to choose from; when nothing matches it
falls back to the full interactive list.

### Selection metadata (使用する場面 / 使用条件)

Each `template.yaml` carries a `selection` block describing **what situations**
the template serves and **when** it applies:

```yaml
selection:
  use_cases:                       # 使用する場面 — scenarios this template fits
    - "Sample Go application with an Nginx proxy and a PostgreSQL database"
  tags:                            # capability/stack tags (category:value or bare)
    - web
    - api
    - lang:go
    - proxy:nginx
    - db:postgres
  keywords: [go, golang, postgres, rest, relational]   # synonyms for matching
  conditions:                      # 使用条件 — prerequisites & boundaries
    requires_docker: true
    services: [postgres]
    notes:
      - "Intended for local development; not production-ready as-is."
```

Scoring priority is tags > keywords > use-cases > name/description text.
`required_tags` hard-filter the catalog, `preferred_tags` add weight, and a
known-unavailable Docker environment excludes Docker-only templates. The logic
lives in [`scaffolder-core/src/orchestrator.rs`](../../crates/scaffolder-core/src/orchestrator.rs)
and is reusable on its own (`auto_select`, `rank`, `SelectionQuery`).

## Available templates

The registered set lives in [`template.yaml`](./template.yaml):

- **Compose stacks**: `fastapi`, `flask`, `django`, `nginx-golang`,
  `nginx-nodejs-redis`, `spring-postgres`, `wordpress-mysql`,
  `prometheus-grafana`, `postgresql-pgadmin`, …
- **Reference packs** (`kind:reference`): `awesome` (the meta-list),
  `awesome-python`, `awesome-go`, `awesome-java`, `awesome-cpp`, `awesome-nodejs`,
  `awesome-react`, `awesome-react-components`, `awesome-selfhosted`,
  `awesome-scalability`, `awesome-design-patterns`, `awesome-hacking`,
  `book-of-secret-knowledge`, `papers-we-love`, `awesome-mac`, `awesome-ios`,
  `awesome-flutter`, `awesome-android-ui`, `open-source-ios-apps`,
  `open-source-mac-os-apps`, `hellogithub`, `github-cheat-sheet`, …

## How these were imported

The templates are generated, not hand-written.

### Compose stacks

```bash
# Curated default set / a specific sample / everything
python scripts/import-compose-templates.py /path/to/awesome-compose
python scripts/import-compose-templates.py /path/to/awesome-compose nginx-flask-mongo
python scripts/import-compose-templates.py /path/to/awesome-compose --all
```

For each sample the importer copies every file, writes a `template.yaml` that
lists those files, marks them language-agnostic (`common: ['*']`), and derives
the `selection` metadata from the sample's components and the awesome-compose
index.

### Reference / knowledge packs

```bash
# Curated default set (the awesome-list repos), or a subset by owner/name
python scripts/import-awesome-lists.py
python scripts/import-awesome-lists.py vinta/awesome-python avelino/awesome-go
```

For each list the importer fetches the upstream README, writes `RESOURCES.md`
(with a source + license attribution header), extracts the README's `##`/`###`
headings into a structured `index.yaml`, and generates a `template.yaml` whose
`selection` metadata (tags / keywords / use-cases) is built from a curated
domain table plus the extracted categories. Reference templates are tagged
`kind:reference` and use resource-oriented tags (`lang:python`, `topic:security`,
`platform:ios`, …) — never stack-capability tags — so stack-building intents keep
matching the compose templates. The `REPOS` table in the script is the single
place to add more lists.

## Provenance & license

- **Compose stacks**: Docker [awesome-compose](https://github.com/docker/awesome-compose),
  [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/). Local development
  only; not production-ready as-is.
- **Reference packs**: each list's upstream repo, under its own license (CC0,
  CC-BY, CC-BY-SA, MIT, …). The detected license and source URL are recorded in
  every template's `RESOURCES.md` header, `index.yaml`, and `selection.conditions.notes`.
  The mirrored content is a point-in-time snapshot — visit the source for the
  latest version and to contribute.
