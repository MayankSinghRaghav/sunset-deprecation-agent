# Sunset — the only entrypoint anyone should need.
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- environment ----------------------------------------------------------
.PHONY: install
install: ## uv sync
	uv sync

.PHONY: doctor
doctor: ## Preflight: cluster up, vector round-trip, deps, provider mode
	bash scripts/doctor.sh

# --- database -------------------------------------------------------------
.PHONY: db-up
db-up: ## Bootstrap/start the local Postgres cluster (idempotent)
	bash scripts/pg_bootstrap.sh

.PHONY: db-down
db-down: ## Stop the cluster
	bash scripts/pg_stop.sh

.PHONY: db-reset
db-reset: ## Drop and recreate the sunset database, then re-apply schema
	bash scripts/pg_bootstrap.sh
	uv run python -m datagen.reset

.PHONY: seed
seed: ## Load committed SQL fixtures (deterministic, keyless, no network)
	uv run python -m datagen.load_fixtures

# --- dataset (needs a key; guarded) ---------------------------------------
.PHONY: regen-dataset
regen-dataset: ## Regenerate fixtures from the truth sheet. Changes the golden set.
	uv run python -m datagen.generate --i-understand-this-changes-the-golden-set

.PHONY: embed
embed: ## Generate + commit Gemini embedding fixtures (needs GEMINI_API_KEY)
	uv run python -m datagen.embed

# --- eval -----------------------------------------------------------------
.PHONY: baseline
baseline: ## Score the frozen deterministic rules baseline
	uv run python -m eval.baseline

.PHONY: run
run: ## Run the full 40-feature agent pipeline
	uv run python -m sunset.runner --all

.PHONY: score
score: ## Print the scorecard: baseline vs agent, per trap class
	uv run python -m eval.score

# --- app + tests ----------------------------------------------------------
.PHONY: api
api: ## Serve the FastAPI app
	uv run uvicorn sunset.api.app:app --reload --port 8000

.PHONY: test
test: ## Run the test suite
	uv run pytest

.PHONY: lint
lint: ## ruff check
	uv run ruff check .
