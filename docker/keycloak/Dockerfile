FROM quay.io/keycloak/keycloak:26.3

COPY ./entrypoint.sh /entrypoint.sh

COPY ./import/realm-export.json /import/realm-export.json

ENTRYPOINT ["/entrypoint.sh"]
