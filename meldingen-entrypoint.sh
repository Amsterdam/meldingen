#!/usr/bin/env bash
set -eux

# Run Alembic migrations
alembic upgrade head

# Create users and groups
python main.py add-user user@example.com
python main.py add-user admin@example.com

python main.py add-group admins

python main.py add-casbin-rules

exec "$@"
