# Apache Camel PoC

This PoC runs Apache Camel as a separate container in the existing Docker Compose stack.
It exposes a local HTTP endpoint that fetches a bearer token from the configured OIDC provider on demand.
It also exposes a second local HTTP endpoint that pulls data from the Meldingen API.

## What it proves

- Camel starts locally without adding Java tooling to this repository.
- Camel can fetch a local development token from Keycloak without polling.
- Camel can proxy the protected Meldingen `/melding` endpoint with a fresh bearer token.
- Route changes stay isolated in `camel/routes/`.

## Start the stack

From the repository root:

```bash
cp .env.example .env
docker compose up -d --build meldingen
docker compose up -d keycloak camel
docker compose logs -f camel
```

When the PoC is running, request a token from Camel itself:

```bash
curl -X POST http://127.0.0.1:8088/bearer-token
```

That returns a plain-text value in the form `Bearer <access-token>`.

You can also pull the configured protected API endpoint through Camel:

```bash
curl http://127.0.0.1:8088/pull
```

## Route files

Camel loads these route files:

- `camel/routes/auth.config.yaml`
- `camel/routes/pull.camel.yaml`

Camel listens on `127.0.0.1:8088` on the host and is only published on loopback.
Inside Docker Compose it still reaches Keycloak over `http://keycloak:8002`.

The pull route calls `CAMEL_API_URL + /melding`.

## Token endpoint behavior

The default local setup uses the Keycloak realm's direct access grant with the pre-seeded development user:

- client id: `meldingen`
- username: `user@example.com`
- password: `password`

Those defaults are only meant for local development. They are currently hardcoded in `docker-compose.yml` and passed into Camel as environment variables.

If you need different values, change the Camel service in `docker-compose.yml` or add a Compose override file.

The auth route supports two practical grant shapes:

- `password` for the local Keycloak user flow.
- `client_credentials` for service-to-service tokens such as Entra app registrations.

The auth route decides between them using `CAMEL_OIDC_GRANT_TYPE`.

If you use `client_credentials`, you must also set `CAMEL_OIDC_CLIENT_SECRET`, and the `CAMEL_OIDC_SCOPE_ENCODED` value should be URL-encoded.

## Consequences for Keycloak vs Entra ID

This backend does not just validate a signature. It also requires a specific user-identifying claim and uses that claim to look up or create an application user.

- Local Keycloak is configured for a user token flow that works well in a PoC: the `meldingen` client is public and has direct access grants enabled.
- Production Entra ID should not be treated as a drop-in replacement for that route. A username/password grant is often blocked by MFA, conditional access, or tenant policy, and in many setups it is not allowed at all.
- A client-credentials token is also not equivalent here. The backend currently requires a user claim such as `email`, while app-only tokens usually identify the calling application instead of a human user.
- The token URL differs by runtime location. Inside local Docker, Camel must use the internal Keycloak hostname. In production, Camel would use Entra's public token endpoint.
- The requested permissions differ as well. Keycloak is using local OIDC scopes like `openid email profile`, while Entra usually needs app registration-specific scopes or `.default` depending on whether you want delegated or app-only access.

Two practical consequences follow from that:

- If Camel only needs to call this backend locally, the Keycloak password-grant path is the shortest PoC because it yields a token with the email claim this backend already expects.
- If Camel must represent a service in production, you either need an Entra delegated flow that still yields a user identity, or you need backend changes so app-only tokens are accepted intentionally.

If you want a production-shaped Camel integration, the next design choice is whether Camel should act as a user or as a service. That choice determines whether the right follow-up is an Entra delegated flow, an on-behalf-of flow, or backend changes to accept service principal tokens.