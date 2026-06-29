#!/usr/bin/env bash
# End-to-end integration test (Phase 0): build & start the iii engine, start the
# arbitrage Python worker, then run the gated pytest E2E suite that drives the
# one-item flow over the real engine (source → research → fx → profit → evaluate
# → draft → ledger), all in dry-run. Tears everything down on exit.
#
# Usage:  scripts/arb-e2e.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

III_URL="ws://localhost:49199"
# No OTLP collector in the E2E sandbox — disable telemetry export.
export III_TELEMETRY_ENABLED="false"
# Keep the worker in dry-run: no external posts/notifications during E2E.
export ARB_DRY_RUN="true"
ARB_PID=""

log() { printf '\n\033[1;36m[arb-e2e]\033[0m %s\n' "$*"; }

cleanup() {
  log "tearing down…"
  [[ -n "$ARB_PID" ]] && kill "$ARB_PID" 2>/dev/null || true
  make engine-down 2>/dev/null || true
}
trap cleanup EXIT

log "pre-flight cleanup (stale workers / engine)…"
pkill -9 -f "src.worker.app" 2>/dev/null || true
make engine-down 2>/dev/null || true
sleep 1

log "building engine (cargo, may take a few minutes)…"
make engine-build

log "starting engine on $III_URL …"
make engine-up

log "preparing arbitrage venv + iii SDK…"
make install-arb
( cd apps/arbitrage && uv pip install -e ../../sdk/packages/python/iii >/dev/null )

log "starting arbitrage worker…"
( cd apps/arbitrage && III_URL="$III_URL" uv run --no-project python -m src.worker.app >/tmp/arb-e2e.log 2>&1 ) &
ARB_PID=$!

log "waiting for worker to register…"
sleep 6

log "running E2E suite…"
( cd apps/arbitrage && III_E2E=1 III_URL="$III_URL" uv run --no-project pytest tests/e2e -q )

log "E2E passed ✅"
