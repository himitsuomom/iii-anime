#!/usr/bin/env bash
# End-to-end integration test (Phase 4): build & start the iii engine, start the
# EC Python worker and the automation-studio Node worker, then run the gated
# pytest E2E suite that drives them over the real engine (sync trigger, async
# queue, state tracking). Tears everything down on exit.
#
# Usage:  scripts/ec-e2e.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

III_URL="ws://localhost:49199"
EC_PID=""
AS_PID=""

log() { printf '\n\033[1;36m[e2e]\033[0m %s\n' "$*"; }

cleanup() {
  log "tearing down…"
  [[ -n "$EC_PID" ]] && kill "$EC_PID" 2>/dev/null || true
  [[ -n "$AS_PID" ]] && kill "$AS_PID" 2>/dev/null || true
  make engine-down 2>/dev/null || true
}
trap cleanup EXIT

log "pre-flight cleanup (stale workers / engine)…"
pkill -9 -f "src.worker.app" 2>/dev/null || true
pkill -9 -f "tsx server/index.ts" 2>/dev/null || true
make engine-down 2>/dev/null || true
sleep 1

log "building engine (cargo, may take a few minutes)…"
make engine-build

log "starting engine on $III_URL …"
make engine-up

log "preparing EC venv + iii SDK…"
make install-ec
( cd apps/ec && uv pip install -e ../../sdk/packages/python/iii >/dev/null )

log "building iii node SDK (+ observability dep) + starting automation-studio worker…"
pnpm --filter @iii-dev/observability build >/dev/null 2>&1 || log "warn: observability build failed"
pnpm --filter iii-sdk build >/dev/null 2>&1 || log "warn: iii-sdk build failed (AS worker may not start)"
# AS worker only needs the iii registration; use a non-default HTTP port to avoid
# colliding with any stray 8787 listener.
( III_URL="$III_URL" PORT=8799 pnpm --filter @iii/automation-studio start >/tmp/ec-e2e-as.log 2>&1 ) &
AS_PID=$!

log "starting EC worker…"
( cd apps/ec && III_URL="$III_URL" uv run --no-project python -m src.worker.app >/tmp/ec-e2e-ec.log 2>&1 ) &
EC_PID=$!

log "waiting for workers to register…"
sleep 6

log "running E2E suite…"
( cd apps/ec && III_E2E=1 III_URL="$III_URL" uv run --no-project pytest tests/e2e -q )

log "E2E passed ✅"
