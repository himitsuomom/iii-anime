# Open Notebook

[Open Notebook](https://github.com/lfnovo/open-notebook) is an open-source,
privacy-focused alternative to Google's NotebookLM. It lets you organize
research into notebooks, ingest PDFs / web pages / audio / video, chat with your
content using 18+ AI providers, and generate podcasts and AI notes — all
self-hosted, with your data under your control.

This directory vendors the **deployment configuration** for running Open
Notebook as a standalone app alongside the iii monorepo. It runs from the
official published Docker images (`lfnovo/open_notebook` + `surrealdb`); no
application source is copied here, so it stays decoupled from iii and easy to
upgrade by bumping the image tags.

## Components

| Service        | Image                          | Purpose                  | Port(s)            |
| -------------- | ------------------------------ | ------------------------ | ------------------ |
| `open_notebook`| `lfnovo/open_notebook:v1-latest` | Web UI + REST API      | `8502` UI, `5055` API |
| `surrealdb`    | `surrealdb/surrealdb:v2`       | Database (persistence)   | `8000`             |

## Quick start

Requires Docker Desktop (or Docker Engine + Compose v2).

```bash
cd apps/open-notebook

# 1. Create your local env file and set a real encryption key
cp .env.example .env
#   then edit .env and change OPEN_NOTEBOOK_ENCRYPTION_KEY to a secret string
#   (16+ chars). The compose file refuses to start if it is unset.

# 2. Launch
docker compose up -d

# 3. Wait ~15-20s for initialization, then open:
#    http://localhost:8502   (Web UI)
#    http://localhost:5055   (REST API)
```

Stop and remove the containers with `docker compose down` (data persists in the
bind-mounted `surreal_data/` and `notebook_data/` directories, which are
git-ignored).

## Configuration

All configuration lives in `.env` (copied from `.env.example`):

- **`OPEN_NOTEBOOK_ENCRYPTION_KEY`** (required) — encrypts API keys stored in the
  database. Must be changed from the default.
- **`SURREAL_USER` / `SURREAL_PASSWORD`** — default to `root:root` for local use.
  Change these before exposing the instance to a network; the compose file
  applies them to both the database and the app so they stay in sync.
- **AI provider keys** (optional) — `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
  Recommended to configure these via the UI (Settings → API Keys) instead.

See the upstream
[environment reference](https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/environment-reference.md)
for the full list of options.

## Upgrading

Bump the image tags in `docker-compose.yml` (e.g. `lfnovo/open_notebook:v1-latest`),
then:

```bash
docker compose pull
docker compose up -d
```

## Upstream

- Repository: <https://github.com/lfnovo/open-notebook>
- License: see the upstream repository (this directory contains only deployment
  config and documentation, not Open Notebook's source code).
