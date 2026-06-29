# apps/arbitrage — 越境転売 automation iii worker (Python 3.11).
# Build from the repo root so the local iii Python SDK can be copied in:
#   docker build -f apps/arbitrage/Dockerfile -t iii-arbitrage-worker .
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Optional: space-separated hosts to mark trusted for pip (e.g. behind a
# TLS-intercepting corporate/CI proxy). Empty by default = normal TLS verify.
ARG PIP_TRUSTED_HOSTS=""

# 1) Runtime dependencies (all pure-Python wheels — no build toolchain needed).
COPY apps/arbitrage/requirements.txt ./requirements.txt
RUN PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install -r requirements.txt

# 2) Local iii Python SDK. iii-sdk depends on iii-observability==0.19.4 via a
#    path source, so install observability first to satisfy it locally.
COPY sdk/packages/python/observability /opt/iii-observability
COPY sdk/packages/python/iii /opt/iii-sdk
RUN PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install /opt/iii-observability \
    && PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install /opt/iii-sdk

# 3) Application source + config.
COPY apps/arbitrage/pyproject.toml ./pyproject.toml
COPY apps/arbitrage/config ./config
COPY apps/arbitrage/src ./src

# Connects to the engine; overridden by compose. Telemetry off and dry-run on by
# default — no external posts/notifications until explicitly enabled.
ENV III_URL=ws://engine:49134 \
    III_TELEMETRY_ENABLED=false \
    ARB_DRY_RUN=true

CMD ["python", "-m", "src.worker.app"]
