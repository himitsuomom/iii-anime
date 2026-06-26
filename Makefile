# ── Configuration ─────────────────────────────────────────────────────────────

TEST_ENGINE_CONFIG  := sdk/fixtures/config-test.yaml
BRIDGE_BE_CONFIG    := sdk/fixtures/config-bridge-backend.yaml
BRIDGE_CONFIG       := sdk/fixtures/config-bridge.yaml
ENGINE_BIN          := ./target/debug/iii
START_SCRIPT        := bash scripts/start-iii.sh
STOP_SCRIPT         := bash scripts/stop-iii.sh
III_URL             := ws://localhost:49199
III_HTTP_URL        := http://localhost:3199
PYTHON_SDK_DIR      := sdk/packages/python/iii
EC_DIR              := apps/ec

export III_TELEMETRY_ENABLED := false

.PHONY: install install-node install-python install-hooks \
        engine-build engine-test engine-fmt-check \
        engine-up engine-up-bridges engine-down \
        init-build-x86 init-build-aarch64 init-build-all \
        sandbox sandbox-debug \
        test-sdk-node test-sdk-python test-sdk-rust test-sdk-all \
        install-ec lint-ec typecheck-ec test-ec ci-ec contracts-codegen seed-demo \
        compose-build compose-up compose-down \
        lint-python lint-rust lint-console lint \
        fmt-check fmt-check-rust fmt-check-all \
        typecheck-node typecheck-python typecheck \
        build-node build-sdk-node build-console build \
        fix fix-lint fix-fmt \
        check ci-engine ci-sdk-node ci-sdk-python ci-sdk-rust \
        ci-console ci-local cli-docs

# ── Setup ─────────────────────────────────────────────────────────────────────

install: install-node install-python

install-node:
	pnpm install --frozen-lockfile

install-python:
	cd $(PYTHON_SDK_DIR) && uv sync --extra dev

install-hooks:
	git config core.hooksPath .githooks
	@echo "[hooks] pre-commit installed (core.hooksPath=.githooks)"


# ── EC app (apps/ec — POD resale automation, Python) ────────────────────────────
# Uses requirements.txt + a local .venv (not uv-project mode). Tests mock all
# external APIs, so `test-ec` runs fully offline with no API key.

install-ec:
	cd $(EC_DIR) && uv venv --python 3.11 && uv pip install -r requirements.txt

lint-ec:
	cd $(EC_DIR) && uv run --no-project ruff check src

typecheck-ec:
	cd $(EC_DIR) && uv run --no-project mypy src

test-ec:
	cd $(EC_DIR) && uv run --no-project pytest -q

# Seed sample orders/inventory into a running engine (requires engine + EC worker
# up, e.g. via scripts/ec-e2e.sh or `make engine-up` + the worker). Lets the
# dashboard show real KPIs without a live Shopify store.
seed-demo:
	cd $(EC_DIR) && III_URL=$(III_URL) uv run --no-project python ../../scripts/seed-demo.py


# ── Local container stack (deploy/docker-compose.yml) ───────────────────────────
# Brings up engine + EC worker + automation-studio. The engine image copies a
# pre-built binary, so stage the debug build into engine/iii-$(ARCH) first.

COMPOSE      := docker compose -f deploy/docker-compose.yml
COMPOSE_ARCH := $(if $(filter x86_64,$(shell uname -m)),amd64,arm64)

compose-build:
	cargo build -p iii --all-features
	cp target/debug/iii engine/iii-$(COMPOSE_ARCH)
	$(COMPOSE) build

compose-up: compose-build
	$(COMPOSE) up -d
	@echo "automation-studio UI/API: http://localhost:8787"
	@echo "engine: ws://localhost:49134 (HTTP http://localhost:3111)"

compose-down:
	$(COMPOSE) down


# ── Contracts (packages/contracts — JSON Schema → TS & Pydantic) ─────────────────
# schemas/*.json is the single source of truth; regenerate both targets from it.

CONTRACTS_DIR := packages/contracts

contracts-codegen:
	cd $(CONTRACTS_DIR) && \
		npx -y json-schema-to-typescript@15 schemas/commerce.schema.json \
			--unreachableDefinitions --no-additionalProperties \
			> generated/typescript/commerce.ts && \
		uvx --from datamodel-code-generator datamodel-codegen \
			--input schemas/commerce.schema.json --input-file-type jsonschema \
			--output generated/python/commerce.py
	@echo "[contracts] regenerated TS + Pydantic from schemas/commerce.schema.json"


ci-ec: install-ec lint-ec test-ec


# ── Engine ────────────────────────────────────────────────────────────────────

engine-build:
	cargo build -p iii --all-features

engine-test:
	cargo test -p iii --all-features

engine-fmt-check:
	cargo fmt --all -- --check

engine-up:
	$(START_SCRIPT) --binary $(ENGINE_BIN) --config $(TEST_ENGINE_CONFIG) --port 49199

engine-up-bridges: engine-up
	$(START_SCRIPT) --binary $(ENGINE_BIN) \
		--config $(BRIDGE_BE_CONFIG) --port 49198 \
		--pid-file /tmp/iii-backend.pid --log-file /tmp/iii-backend.log
	$(START_SCRIPT) --binary $(ENGINE_BIN) \
		--config $(BRIDGE_CONFIG) --port 49197 \
		--pid-file /tmp/iii-bridge.pid --log-file /tmp/iii-bridge.log

engine-down:
	$(STOP_SCRIPT) /tmp/iii-engine.pid /tmp/iii-backend.pid /tmp/iii-bridge.pid

# ── Init Binary Cross-Compilation ────────────────────────────────────────────

INIT_CRATE := iii-init
WORKER_CRATE := iii-worker
WORKER_EMBED_FEATURES := embed-init,embed-libkrunfw

init-build-x86:
	cargo build -p $(INIT_CRATE) --target x86_64-unknown-linux-musl --release

init-build-aarch64:
	cargo build -p $(INIT_CRATE) --target aarch64-unknown-linux-musl --release

init-build-all: init-build-x86 init-build-aarch64

# ── Sandbox (init + engine/worker with embedded assets) ──────────────────────
# Auto-detects host arch for the correct musl init target.

UNAME_M := $(shell uname -m)
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_M),x86_64)
  INIT_TARGET := x86_64-unknown-linux-musl
else
  INIT_TARGET := aarch64-unknown-linux-musl
endif

ifeq ($(UNAME_S),Darwin)
  ifeq ($(UNAME_M),x86_64)
    WORKER_TARGET := x86_64-apple-darwin
  else
    WORKER_TARGET := aarch64-apple-darwin
  endif
else
  ifeq ($(UNAME_M),x86_64)
    WORKER_TARGET := x86_64-unknown-linux-gnu
  else
    WORKER_TARGET := aarch64-unknown-linux-gnu
  endif
endif

sandbox: ## Release-like local build: init + engine + worker(embed-init,embed-libkrunfw)
	cargo build -p $(INIT_CRATE) --target $(INIT_TARGET) --release
	cargo build --release -p iii
	cargo build -p $(WORKER_CRATE) --target $(WORKER_TARGET) --features $(WORKER_EMBED_FEATURES) --release

sandbox-debug: ## Release-like local debug: init + engine + worker(embed-init,embed-libkrunfw)
	cargo build -p $(INIT_CRATE) --target $(INIT_TARGET) --release
	cargo build -p iii
	cargo build -p $(WORKER_CRATE) --target $(WORKER_TARGET) --features $(WORKER_EMBED_FEATURES)

# ── SDK Tests ─────────────────────────────────────────────────────────────────

test-sdk-node:
	III_URL=$(III_URL) III_HTTP_URL=$(III_HTTP_URL) \
		pnpm --filter iii-sdk test:coverage

test-sdk-python:
	cd $(PYTHON_SDK_DIR) && \
		III_URL=$(III_URL) III_HTTP_URL=$(III_HTTP_URL) \
		uv run pytest -q

test-sdk-rust:
	III_URL=$(III_URL) III_HTTP_URL=$(III_HTTP_URL) \
		cargo test -p iii-sdk --all-features

test-sdk-all: test-sdk-node test-sdk-python test-sdk-rust

# ── Lint ──────────────────────────────────────────────────────────────────────

lint-python:
	cd $(PYTHON_SDK_DIR) && uv run ruff check src

lint-rust:
	cargo clippy -p iii-sdk --all-targets --all-features -- -D warnings

lint-console:
	pnpm --filter console-frontend lint

lint: lint-python lint-rust lint-console

# ── Format Check ──────────────────────────────────────────────────────────────

fmt-check-rust:
	cargo fmt -p iii-sdk -- --check

fmt-check-all: engine-fmt-check fmt-check-rust

# ── Type Check ────────────────────────────────────────────────────────────────

typecheck-node:
	pnpm --filter iii-sdk exec tsc --noEmit

typecheck-python:
	cd $(PYTHON_SDK_DIR) && uv run mypy src

typecheck: typecheck-node typecheck-python

# ── Build ─────────────────────────────────────────────────────────────────────

build-sdk-node:
	pnpm --filter iii-sdk build

build-console:
	pnpm --filter console-frontend build
	cargo build -p iii-console --release

build: sandbox build-console ## Build everything: init + engine + worker + console
	@echo ""
	@echo "Build complete. Binaries:"
	@echo "  engine:   $(CURDIR)/target/release/iii"
	@echo "  console:  $(CURDIR)/target/release/iii-console"
	@echo "  worker:   $(CURDIR)/target/$(WORKER_TARGET)/release/iii-worker"
	@echo ""
	@echo "Add them to your PATH:"
	@echo '  export PATH="$(CURDIR)/target/release:$(CURDIR)/target/$(WORKER_TARGET)/release:$$PATH"'

# ── CI Jobs (mirror ci.yml) ──────────────────────────────────────────────────

ci-engine: engine-build engine-test engine-fmt-check

ci-sdk-node: engine-up-bridges
	@trap '$(MAKE) engine-down' EXIT; \
	$(MAKE) typecheck-node build-sdk-node test-sdk-node

ci-sdk-python: engine-up
	@trap '$(MAKE) engine-down' EXIT; \
	$(MAKE) install-python lint-python typecheck-python test-sdk-python

ci-sdk-rust: engine-up
	@trap '$(MAKE) engine-down' EXIT; \
	$(MAKE) fmt-check-rust lint-rust test-sdk-rust

ci-console:
	$(MAKE) lint-console build-console

# ── Convenience ───────────────────────────────────────────────────────────────

cli-docs: ## Regenerate docs/next/cli-reference/ from the clap CLI definitions
	./scripts/generate-cli-docs.sh

fix: fix-fmt fix-lint

fix-fmt:
	cargo fmt --all

fix-lint:
	cd $(PYTHON_SDK_DIR) && uv run ruff check --fix --unsafe-fixes src && uv run ruff format src
	cargo clippy -p iii-sdk --all-targets --all-features --fix --allow-dirty --allow-staged -- -D warnings
	pnpm --filter console-frontend run lint:fix

check: lint fmt-check-all typecheck build-sdk-node build-console

ci-local: ci-engine ci-sdk-node ci-sdk-python ci-sdk-rust ci-console
