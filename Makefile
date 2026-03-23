.PHONY: help build push up rebuild lint typecheck typecheck-sync test test-coverage

REGISTRY ?= localhost:5000
VERSION ?= latest
INSTALL_DEV ?= false
UID:=$(shell id --user)
GID:=$(shell id --group)
TEST ?= # used to add testpath as argument to pytest, e.g. TEST=tests/api/v1/endpoints/test_melding.py

dc = docker compose
api = $(dc) run --rm --user=root meldingen

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

### DEV ###

up: ## Start Docker Compose stack (detached)
	$(dc) up -d

rebuild: ## Rebuild and start Docker Compose stack (detached)
	$(dc) up -d --build

lint: ## Auto-fix formatting (black + isort)
	$(api) uv run black .
	$(api) uv run isort .

typecheck: ## Run mypy type checking
	$(api) sh -c "uv run mypy --strict . | uv run mypy-baseline filter"

typecheck-sync: ## Run mypy type checking and update baseline
	$(api) sh -c "rm -rf .mypy_cache && uv run mypy --strict . | uv run mypy-baseline sync"

test: ## Run pytest (optional: make test TEST=tests/...)
	$(api) pytest --test-alembic -v -n auto $(TEST)

test-coverage: ## Run pytest with coverage and enforce minimum threshold
	$(api) pytest --test-alembic --cov --cov-fail-under=95 -n auto --cov-report=html -v $(TEST)


### CI ###

build/%:
	cp .env.example .env
	$(dc) build $*

push/%:
	$(dc) push $*
