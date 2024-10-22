#!/usr/bin/env bash
set -eux

if [ "$1" = "fastapi" ]; then
  # Run Alembic migrations
  alembic upgrade head

  # Run Python commands (ignoring errors)
  python main.py users add user@example.com || true
  python main.py static-forms create || true
fi

exec "$@"
