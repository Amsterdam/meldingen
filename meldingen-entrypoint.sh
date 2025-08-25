#!/usr/bin/env bash
set -eux

if [ "$1" = "fastapi" ] || [ "$1" = "uvicorn" ]; then
  # Run Alembic migrations
  alembic upgrade head

  # Run Python commands (ignoring errors)
  python main.py users add user@example.com || true
  python main.py static-forms create || true
  python main.py azure create-container || true
  python main.py asset_types add container meldingen.wfs.ProxyWfsProviderFactory https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval || true
fi

exec "$@"
