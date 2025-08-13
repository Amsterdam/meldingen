#!/usr/bin/env bash
docker compose exec keycloak bash -c "cp -rp /opt/keycloak/data/h2 /tmp ; /opt/keycloak/bin/kc.sh export --realm meldingen --file /import/realm-export.json --db dev-file --db-url 'jdbc:h2:file:/tmp/h2/keycloakdb;NON_KEYWORDS=VALUE'"
