# anime-studio

An **AI anime production pipeline run as a studio (会社として回す)**, built on the
[iii](https://github.com/iii-hq/iii) orchestration engine.

A **director agent (監督)** decomposes the work into a task DAG and runs a roster of
**specialized department agents** in dependency order, applying quality gates
between stages and requesting bounded revisions when a gate fails — mirroring the
AniME / AniMaker "Director Agent統括 + Specialized Agents" architecture and a real
anime studio's org structure.

Departments:

| Stage | 部署 | Output |
|-------|------|--------|
| `planning` | 企画 (STEPPS) | creative/viral strategy |
| `script` | 脚本 | 5-beat Save-the-Cat Shorts script |
| `character` | 設定・キャラデザ | character sheet + LoRA notes |
| `storyboard` | 絵コンテ | per-cut composition / camera / shot size |
| `production` | 作画・素材生成 | per-cut generation prompts (12 principles) |
| `editing` | 編集・音響 | beat-match / BPM / leitmotif / loop plan |
| `qa` | 品質管理 | AniEval-style quality gates |
| `distribution` | 配信最適化 | per-platform variants, thumbnail, titles |

The craft "laws/principles" from the source reports are encoded as an editable
**knowledge base** (`src/anime_studio/knowledge/data/*.yaml`) that every agent
consults — so the studio's craft can be tuned without touching code.

## Providers (adapter + mock-first)

Each AI capability (LLM, image, video, audio, edit) is a swappable **provider
adapter**. Today the pipeline ships **deterministic mocks** plus an **Anthropic
LLM adapter** that transparently degrades to mock when there's no API key or
network. Real image/video/audio/edit adapters (AniSora / WAN / Kling, etc.) slot
into `providers/registry.py` later without touching the agents.

The core deliverable is a complete **production bible** (`production_bible.md`) plus
structured JSON artifacts. With the optional **`render` extra** the studio also
produces a **playable animatic** — a real `.mp4` built from the storyboard (one
9:16 panel per cut, held for its beat-matched duration) plus a storyboard contact
sheet. `imageio-ffmpeg` bundles a static ffmpeg binary, so **no system ffmpeg
install is required**. (Photoreal per-cut video via AniSora/WAN/Kling remains the
provider seam to fill next.)

## Quickstart (standalone, no engine)

```bash
make install-anime              # from repo root, or: uv sync --extra dev
cd apps/anime-studio
uv run anime-studio run --brief tests/fixtures/sample_brief.yaml --output-dir ./output
cat output/demo-sheep/production_bible.md
```

Render a playable animatic mp4 (needs the optional render extra):

```bash
uv sync --extra dev --extra render   # or: uv sync --extra render
uv run anime-studio run --brief tests/fixtures/sample_brief.yaml --render
# -> output/demo-sheep/render/animatic.mp4 + storyboard_contactsheet.png

# With procedural audio (BGM bed + leitmotif SE mixed in -> animatic_av.mp4):
ANIME_STUDIO_AUDIO_PROVIDER=ffmpeg \
  uv run anime-studio run --brief tests/fixtures/sample_brief.yaml --render
```

Real generation (degrades to mock/procedural without keys): set
`[image] [video] [audio]` `provider = "hosted"` in `anime_studio.toml` with
`endpoint` / `model` / `api_key_env`. Real per-cut clips are then concatenated
into `render/final.mp4`; otherwise the storyboard-panel animatic is used.

Other commands:

```bash
uv run anime-studio info        # list departments + dependencies
uv run anime-studio validate    # validate the knowledge base
```

With the real LLM (degrades to mock automatically if unavailable):

```bash
ANIME_STUDIO_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... \
  uv run anime-studio run --brief tests/fixtures/sample_brief.yaml
```

## As an iii worker

```bash
make engine-up                                      # from repo root
cd apps/anime-studio
III_URL=ws://localhost:49199 uv run python -m anime_studio.worker.main
# registers: studio::run_pipeline, studio::render, studio::status,
#            studio::script, studio::storyboard, studio::qa, studio::distribution
```

Then drive the HTTP trigger (the repo test engine serves HTTP on `:3199`):

```bash
curl -X POST http://localhost:3199/studio/run \
     -H 'Content-Type: application/json' -d @tests/fixtures/sample_brief.json
curl http://localhost:3199/studio/status/<project_id>
```

## Config

`anime_studio.toml` (committed defaults) + env overrides:
`ANIME_STUDIO_OUTPUT_DIR`, `ANIME_STUDIO_LLM_PROVIDER`, `ANIME_STUDIO_LLM_MODEL`,
`ANIME_STUDIO_MAX_REVISIONS`, `ANTHROPIC_API_KEY`.

## Develop

```bash
uv run pytest -q          # deterministic suite (mock providers)
uv run ruff check src
uv run mypy src
```
