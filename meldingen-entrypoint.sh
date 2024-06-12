#!/usr/bin/env bash
set -eux

# Run Alembic migrations
alembic upgrade head

# Run Python commands (ignoring errors)
#python main.py users add user@example.com || true
#python main.py static-forms add-primary --title "Hoofd formulier" || true

exec "$@"
