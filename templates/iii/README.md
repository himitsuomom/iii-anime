# iii compose-sample templates

A scaffolding template store for iii, populated with Docker Compose stacks
adapted from Docker's [awesome-compose](https://github.com/docker/awesome-compose)
samples. Each subdirectory is a ready-to-run multi-service stack that the iii
scaffolder can drop into a new project.

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

The registered set lives in [`template.yaml`](./template.yaml). It currently
includes lean, self-contained stacks such as `fastapi`, `flask`, `django`,
`nginx-golang`, `nginx-nodejs-redis`, `spring-postgres`, `wordpress-mysql`,
`prometheus-grafana`, and `postgresql-pgadmin`.

## How these were imported

The templates are generated, not hand-written. To (re)import from a local
awesome-compose checkout:

```bash
# Curated default set
python scripts/import-compose-templates.py /path/to/awesome-compose

# A specific sample
python scripts/import-compose-templates.py /path/to/awesome-compose nginx-flask-mongo

# Everything (skips vendored junk: lockfiles, images, logs)
python scripts/import-compose-templates.py /path/to/awesome-compose --all
```

For each sample the importer copies every file, writes a `template.yaml` that
lists those files, marks them all language-agnostic (`common: ['*']`, so the
scaffolder copies the whole stack regardless of language selection), and
derives the `selection` metadata (tags / keywords / use-cases / services) from
the sample's components and the awesome-compose index. It then registers the
sample in this directory's root `template.yaml`.

## Provenance & license

Source: Docker [awesome-compose](https://github.com/docker/awesome-compose),
released under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/)
(public domain dedication). These samples are intended for local development and
are not production-ready as-is.
