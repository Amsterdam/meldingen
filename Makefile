.PHONY: help build push up rebuild lint typecheck typecheck-sync test test-pdb test-coverage update check-all migration migrate upgrade-core switch-core
REGISTRY ?= localhost:5000
VERSION ?= latest
INSTALL_DEV ?= false
UID:=$(shell id --user)
GID:=$(shell id --group)
TEST ?= # used to add testpath as argument to pytest, e.g. TEST=tests/api/v1/endpoints/test_melding.py
CORE_BRANCH ?= main

dc = docker compose
api = $(dc) run --rm --user=root meldingen

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

### DEV ###

up: ## Start Docker Compose stack (detached)
	$(dc) up -d

rebuild: ## Rebuild and start Docker Compose stack (detached)
	$(dc) up -d --build

format: ## Auto-fix formatting (black + isort)
	$(api) uv run black .
	$(api) uv run isort .

typecheck: ## Run mypy type checking
	$(api) sh -c "rm -rf .mypy_cache && uv run mypy --strict . | uv run mypy-baseline filter"

typecheck-sync: ## Run mypy type checking and update baseline
	$(api) sh -c "rm -rf .mypy_cache && uv run mypy --strict . | uv run mypy-baseline sync"

test: ## Run pytest (optional: make test TEST=tests/...)
	$(api) pytest --test-alembic -v -n auto $(TEST)

test-pdb: ## Run pytest with python debugger on failure (optional: make test-pdb TEST=tests/...)
	$(api) pytest --test-alembic -v -n auto --pdb $(TEST)

test-coverage: ## Run pytest with coverage and enforce minimum threshold
	$(api) pytest --test-alembic --cov --cov-fail-under=95 -n auto --cov-report=html -v $(TEST)

update: ## Update dependencies (uv)
	$(api) uv lock --upgrade

upgrade-core: ## Upgrade only meldingen-core
	$(api) uv lock --upgrade-package meldingen-core

switch-core: ## Switch meldingen-core to a specific branch or otherwise main, e.g. make switch-core CORE_BRANCH=feature/my-branch
	$(api) uv add meldingen-core --branch "$(CORE_BRANCH)"

check-all: ## Run all checks (format, typecheck, test)
	$(MAKE) format
	$(MAKE) typecheck
	$(MAKE) test

migration: ## Create a new Alembic migration (usage: make migration NAME="add new column")
	$(api) alembic revision --autogenerate -m "$(NAME)"

migrate: ## Run Alembic migrations
	$(api) alembic upgrade head

lock: ## Create a new Poetry lock file
	$(api) uv lock

### CI ###

build/%:
	cp .env.example .env
	$(dc) build $*

push/%:
	$(dc) push $*
