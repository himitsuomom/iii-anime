#!/usr/bin/env bash
#
# install.sh — Install the runnable tools from the GitHub stars list "プロンプト".
#
#   Source list: https://github.com/stars/himitsuomom/lists/プロンプト
#
# The list contains 12 repositories, but only a few ship installable software;
# the rest are prompt collections (Markdown) meant to be browsed, not installed.
# This script installs the runnable tools and reports the ones that cannot be
# installed in this environment.
#
# Usage:
#   bash tools/prompt-tools/install.sh
#
set -euo pipefail

GOBIN="${GOBIN:-$HOME/go/bin}"
VENV_DIR="${PROMPT_TOOLS_VENV:-$HOME/.venvs/prompt-tools}"

info()  { printf '\033[1;34m[install]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[skip]\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Fabric (danielmiessler/Fabric) — Go CLI for augmenting humans with AI.
# ---------------------------------------------------------------------------
if command -v go >/dev/null 2>&1; then
  info "Installing Fabric CLI via 'go install'..."
  GOBIN="$GOBIN" go install github.com/danielmiessler/fabric/cmd/fabric@latest
  ok "Fabric installed to $GOBIN/fabric  (add \$HOME/go/bin to PATH)"
  "$GOBIN/fabric" --version || true
else
  warn "Go toolchain not found — cannot install Fabric. See https://go.dev/dl/"
fi

# ---------------------------------------------------------------------------
# 2. Promptify (promptslab/Promptify) — Python LIBRARY (no CLI entrypoint).
#    Installed into a dedicated venv so it does not pollute the project env.
# ---------------------------------------------------------------------------
PY_INSTALLER=""
if command -v uv >/dev/null 2>&1; then
  PY_INSTALLER="uv"
elif command -v python3 >/dev/null 2>&1; then
  PY_INSTALLER="pip"
fi

if [ -n "$PY_INSTALLER" ]; then
  info "Installing Promptify (Python library) into $VENV_DIR ..."
  if [ "$PY_INSTALLER" = "uv" ]; then
    uv venv --python 3.11 "$VENV_DIR"
    uv pip install --python "$VENV_DIR" promptify
  else
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install promptify
  fi
  "$VENV_DIR/bin/python" -c "import promptify; print('Promptify import OK')"
  ok "Promptify installed. Use it from: $VENV_DIR/bin/python"
else
  warn "No Python/uv found — cannot install Promptify."
fi

# ---------------------------------------------------------------------------
# 3. promptsource (bigscience-workshop/promptsource) — NOT installable here.
#    Its PyPI sdist is broken (missing requirements.txt) and it is only
#    reliably installable from its GitHub git repo, which this environment's
#    egress policy blocks (HTTP 403 on github.com git). Install manually on a
#    machine with GitHub access:
#        pip install git+https://github.com/bigscience-workshop/promptsource.git
#    (Requires Python 3.7–3.9.)
# ---------------------------------------------------------------------------
warn "promptsource: skipped — only distributed via GitHub git (egress-blocked here)."

ok "Done. Installable tools from the 'プロンプト' list are set up."
