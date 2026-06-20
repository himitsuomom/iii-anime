#!/bin/bash
# SessionStart hook for Claude Code on the web.
#
# Bootstraps a fresh, ephemeral container so linters and tests are runnable:
#   1. System libraries required to link the Rust workspace (libcap-ng-dev).
#   2. JS/TS + Python dependencies (delegates to `make install`).
#   3. The repo's git hooks (`make install-hooks`).
#
# Safe to run repeatedly (idempotent) and never prompts for input.
set -euo pipefail

# Only run inside the remote (web) environment. On local machines developers
# manage their own toolchain via the README / Makefile.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# ── System dependencies ───────────────────────────────────────────────────────
# `iii-worker` links against libcap-ng; without the -dev package the Rust
# release build fails with `unable to find library -lcap-ng`.
if ! dpkg -s libcap-ng-dev >/dev/null 2>&1; then
  echo "[session-start] installing libcap-ng-dev"
  SUDO=""
  if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  fi
  if command -v apt-get >/dev/null 2>&1; then
    if ! DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y libcap-ng-dev; then
      $SUDO apt-get update && DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y libcap-ng-dev
    fi
  else
    echo "[session-start] apt-get unavailable; skipping libcap-ng-dev (Rust builds may fail to link)" >&2
  fi
fi

# ── Project dependencies ──────────────────────────────────────────────────────
# `make install` runs `pnpm install --frozen-lockfile` and `uv sync --extra dev`
# for the Python SDK. `make install-hooks` wires up the pre-commit format gate.
make install
make install-hooks

echo "[session-start] bootstrap complete"
