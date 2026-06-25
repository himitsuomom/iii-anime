#!/usr/bin/env bash
# Wrapper for the QuDAG MCP server (qudag-cli) over the stdio transport.
#
# Why this wrapper exists:
#   qudag-cli 0.5.0 writes its tracing logs (including a ~10Hz heartbeat) to
#   STDOUT when run with `--transport stdio`. MCP stdio clients treat stdout as
#   the JSON-RPC channel, so those log lines corrupt the protocol stream and the
#   client fails to parse responses. RUST_LOG does not suppress them.
#
# What it does:
#   - Discards the server's own stderr (human-readable banner + any noise).
#   - Filters stdout down to JSON-RPC frames (lines starting with '{') so the
#     client sees a clean protocol stream.
#   - stdin is passed straight through to the server (left-hand side of the
#     pipe inherits this script's stdin), preserving bidirectional JSON-RPC.
#
# This is a workaround for an upstream bug; drop it once qudag-cli routes logs
# to stderr on the stdio transport.
set -euo pipefail

# Ensure the cargo-installed binary is reachable even with a minimal PATH.
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"

exec qudag mcp start --transport stdio 2>/dev/null \
  | grep --line-buffered '^{'
