# Config-baked iii engine image for the ECS runtime.
#
# The upstream engine image (iiidev/iii) is distroless (no shell), so the engine
# config can't be written at runtime via an entrypoint script and ECS can't bind
# a host file. Bake deploy/config.yaml into the image at the path the default
# entrypoint reads (/app/config.yaml). Build from the repo root:
#   docker build -f deploy/engine.Dockerfile -t iii-engine .
FROM iiidev/iii:latest

# Worker WebSocket :49134, HTTP API :3111 (see deploy/config.yaml).
COPY deploy/config.yaml /app/config.yaml
