# video-studio (skeleton)

A **second AI factory** on the same iii engine — video production — that runs
alongside [`app-studio`](../app-studio) and **reuses its hardened sandbox** as
shared "studio-core". This proves the multi-factory thesis: one engine,
multiple domain factories, sharing the execution backbone, differing only in
the domain (brain prompts, tools, adapters, and how "done" is judged).

## What's shared vs domain-specific

| | Shared (studio-core) | Video-specific |
|---|---|---|
| Execution | `app-studio` sandbox — allowlist + workdir confinement + timeout + optional `unshare` isolation (imported verbatim in `src/sandbox.ts`) | `VIDEO_ALLOWLIST` (ffmpeg/ffprobe instead of node/pnpm) |
| Orchestration | the pipeline shape + state machine + approval gate + wiki (pattern reused) | brief → storyboard → render → QA → approval → deliver |
| Brain | the `Brain` abstraction (`claude -p` / API) | storyboard prompts |
| Build/render | the `BuildBackend` abstraction | `ffmpeg` render (assemble image clips → mp4) |
| Adapters | the adapter registry pattern | `slideshow` (image slideshow) |

## The key difference: QA is subjective

Software has an objective "done" (tests pass). Video does not — "good" is a
judgement call. So the video QA rubric (`src/qa.ts`) checks only **objective**
properties (the output exists, `ffprobe` reads a valid duration within
tolerance) and the factory leans on the **human approval gate** (already built
in `app-studio`) for the creative sign-off. Auto-iteration is weaker here;
approval is primary.

## Status

Skeleton with the domain-specific, unit-tested pieces in place:

- `sandbox.ts` — re-exports the shared sandbox + the video allowlist.
- `types.ts` — `Brief` / `Shot` / `Storyboard` / `VideoQa`.
- `storyboard.ts` — `validateStoryboard` (the video analog of `Plan`).
- `render/ffmpeg.ts` — pure ffmpeg arg builders (`imageClipArgs`, `concatArgs`,
  `planRender`) executed through the shared sandbox.
- `qa.ts` — objective rubric + duration tolerance.

```bash
cd video-studio && pnpm exec tsx --test "src/**/*.test.ts"   # 10 tests
```

Tests pass without ffmpeg installed (the builders are pure); a live render needs
`ffmpeg`/`ffprobe` on the host. The shared-sandbox test proves the video factory
runs commands through `app-studio`'s execution boundary (and still rejects
`curl`/shell operators) under the video allowlist.

## Next (to finish the multi-factory extraction)

The orchestrator state machine still hard-codes `studio::*` function ids, so it
isn't imported here yet. The clean follow-up is to lift the generic core
(`machine`/`apply`/`store`/`wiki`/approval) into a `studio-core` package that
both factories depend on, leaving each factory with only its domain handlers,
brain prompts, backend, and adapters — exactly the split this skeleton models.
