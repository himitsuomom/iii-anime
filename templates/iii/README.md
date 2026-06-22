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
lists those files and marks them all language-agnostic (`common: ['*']`, so the
scaffolder copies the whole stack regardless of language selection), and
registers the sample in this directory's root `template.yaml`.

## Provenance & license

Source: Docker [awesome-compose](https://github.com/docker/awesome-compose),
released under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/)
(public domain dedication). These samples are intended for local development and
are not production-ready as-is.
