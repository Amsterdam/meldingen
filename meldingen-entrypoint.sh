#!/usr/bin/env bash
set -eux

extract_emails() {
  # Grep lines containing "email ="
  # and extract the string inside quotes using sed
  grep -oP 'email\s*=\s*"\K[^"]+' "pyproject.toml" || true
}


if [ "$1" = "fastapi" ] || [ "$1" = "uvicorn" ]; then
  # Run Alembic migrations
  alembic upgrade head

  python main.py users add user@example.com || true


  for email in $(extract_emails); do
    echo "Adding user from pyproject.toml: $email"
    python main.py users add "$email" || true
  done

  python main.py static-forms create || true
  python main.py azure create-container || true
  python main.py asset_types add container meldingen.wfs.ProxyWfsProviderFactory 3 https://api.data.amsterdam.nl/v1/wfs/huishoudelijkafval || true
fi

exec "$@"
