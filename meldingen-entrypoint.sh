#!/usr/bin/env bash
set -eux

# Run Alembic migrations
alembic upgrade head

exec "$@"
