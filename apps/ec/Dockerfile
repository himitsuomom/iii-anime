# apps/ec — POD resale automation iii worker (Python 3.11).
# Build from the repo root so the local iii Python SDK can be copied in:
#   docker build -f apps/ec/Dockerfile -t iii-ec-worker .
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Optional: space-separated hosts to mark trusted for pip (e.g. behind a
# TLS-intercepting corporate/CI proxy). Empty by default = normal TLS verify.
ARG PIP_TRUSTED_HOSTS=""

# 1) EC runtime dependencies (all pure-Python wheels — no build toolchain needed).
COPY apps/ec/requirements.txt ./requirements.txt
RUN PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install -r requirements.txt

# 2) Local iii Python SDK. iii-sdk depends on iii-observability==0.19.4 via a
#    path source, so install observability first to satisfy it locally (plain
#    pip would otherwise try to fetch it from PyPI).
COPY sdk/packages/python/observability /opt/iii-observability
COPY sdk/packages/python/iii /opt/iii-sdk
RUN PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install /opt/iii-observability \
    && PIP_TRUSTED_HOST="$PIP_TRUSTED_HOSTS" pip install /opt/iii-sdk

# 3) Application source.
COPY apps/ec/pyproject.toml ./pyproject.toml
COPY apps/ec/src ./src

# Connects to the engine; overridden by compose. Telemetry off unless a
# collector is wired up.
ENV III_URL=ws://engine:49134 \
    III_TELEMETRY_ENABLED=false

CMD ["python", "-m", "src.worker.app"]
