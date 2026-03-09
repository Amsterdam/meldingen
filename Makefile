.PHONY: help build push up rebuild debug lint typecheck test

REGISTRY ?= localhost:5000
VERSION ?= latest
INSTALL_DEV ?= false
UID:=$(shell id --user)
GID:=$(shell id --group)
TEST ?= # used to add testpath as argument to pytest, e.g. TEST=tests/api/v1/endpoints/test_melding.py

dc = docker compose
dc_debug = $(dc) -f docker-compose.yml -f docker-compose.debug.yml

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

### DEV ###

up: ## Start Docker Compose stack (detached)
	$(dc) up -d

rebuild: ## Rebuild and start Docker Compose stack (detached)
	$(dc) up -d --build

debug: ## Start API with debugpy enabled (attach from VS Code)
	$(dc_debug) up -d --build
	@echo "Now attach from VS Code using: Python: Attach (Docker Compose / debugpy)"

lint: ## Auto-fix formatting (black + isort)
	$(dc) run --rm meldingen poetry run black .
	$(dc) run --rm meldingen poetry run isort .

typecheck: ## Run mypy type checking
	$(dc) run --rm --user=root meldingen poetry run mypy --strict . | mypy-baseline filter

typecheck-sync: ## Run mypy type checking and update baseline
	$(dc) run --rm --user=root meldingen poetry run mypy --strict . | mypy-baseline sync

test: ## Run pytest (optional: make test TEST=tests/...)
	$(dc) run --rm meldingen pytest --test-alembic -v -n auto $(TEST)

test-coverage:
	$(dc) run --rm meldingen pytest --test-alembic --cov --cov-fail-under=95 -n auto --cov-report=html -v $(TEST)


### CI ###

build/%:
	cp .env.example .env
	$(dc) build $*

push/%:
	$(dc) push $*
