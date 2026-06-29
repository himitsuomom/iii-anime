# apps/automation-studio — Hono API + React UI + iii worker (Node 22).
# Multi-stage: a full-workspace build stage, then a slim runtime stage that
# carries only the pruned production bundle (pnpm deploy) — no pnpm, no
# workspace, no dev dependencies.
#
# Build from the repo root (the pnpm workspace resolves the local iii SDK):
#   docker build -f apps/automation-studio/Dockerfile -t iii-automation-studio .

# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:22-slim AS build

# Optional: set to "0" to relax TLS verification for the package registry during
# build (e.g. behind a TLS-intercepting corporate/CI proxy). Default "1" = strict.
# Build-stage only — it never reaches the runtime image.
ARG NODE_TLS_REJECT_UNAUTHORIZED=1
ENV NODE_TLS_REJECT_UNAUTHORIZED=${NODE_TLS_REJECT_UNAUTHORIZED}

WORKDIR /repo
RUN corepack enable

# Whole workspace (node_modules/dist/target excluded via root .dockerignore).
COPY . .
RUN pnpm install --frozen-lockfile

# Build the iii SDK deps the worker imports, then the Vite frontend bundle.
RUN pnpm --filter @iii-dev/observability build \
    && pnpm --filter iii-sdk build \
    && pnpm --filter @iii/automation-studio build

# Pruned, self-contained production bundle (tsx is a runtime dependency, so it
# is included). `dist/` is gitignored and thus omitted by deploy — copy the
# freshly built frontend in explicitly.
RUN pnpm --filter=@iii/automation-studio --legacy deploy --prod /prod \
    && cp -r apps/automation-studio/dist /prod/dist

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM node:22-slim AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    PORT=8787 \
    III_URL=ws://engine:49134 \
    III_TELEMETRY_ENABLED=false

COPY --from=build /prod /app
EXPOSE 8787

# tsx runs the TS server; it serves ./dist (UI), the /api routes, and registers
# the iii worker when III_URL is set.
CMD ["node", "--import", "tsx", "server/index.ts"]
