# apps/automation-studio — Hono API + React UI + iii worker (Node 22).
# Build from the repo root (pnpm workspace resolves the local iii SDK):
#   docker build -f apps/automation-studio/Dockerfile -t iii-automation-studio .
FROM node:22-slim

# Optional: set to "0" to relax TLS verification for the package registry during
# build (e.g. behind a TLS-intercepting corporate/CI proxy). Default "1" = strict.
ARG NODE_TLS_REJECT_UNAUTHORIZED=1
ENV NODE_TLS_REJECT_UNAUTHORIZED=${NODE_TLS_REJECT_UNAUTHORIZED}

WORKDIR /repo
RUN corepack enable

# Whole workspace (node_modules/dist/target are excluded via .dockerignore).
COPY . .
RUN pnpm install --frozen-lockfile

# Build the iii SDK deps the worker imports, then the frontend bundle (dist).
RUN pnpm --filter @iii-dev/observability build \
    && pnpm --filter iii-sdk build \
    && pnpm --filter @iii/automation-studio build

WORKDIR /repo/apps/automation-studio
ENV PORT=8787 \
    III_URL=ws://engine:49134 \
    III_TELEMETRY_ENABLED=false
EXPOSE 8787

# `start` runs `tsx server/index.ts`, which serves the built ./dist UI, the
# /api routes, and (when III_URL is set) registers the iii worker.
CMD ["pnpm", "start"]
