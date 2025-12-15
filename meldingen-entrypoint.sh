#!/usr/bin/env bash
set -eux

if [ "$1" = "fastapi" ] || [ "$1" = "uvicorn" ]; then
  # Run Alembic migrations
  alembic upgrade head

  python main.py users add user@example.com || true
  python main.py static-forms create || true
  python main.py azure create-container || true
  python main.py asset_types add container meldingen.wfs.ProxyWfsProviderFactory 3 https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval || true
  python main.py classifications seed || true
fi

exec "$@"
