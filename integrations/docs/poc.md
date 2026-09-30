# Camel Integration PoC

This document captures what the Camel-based integration proof of concept is meant to demonstrate, what was learned during implementation, and what follow-up work would make it more production-shaped.

## What this PoC covers

The current PoC demonstrates four core ideas:

- Camel can sit next to the Meldingen API as an optional integration component rather than pushing municipality-specific logic into the backend.
- A shared internal fetch route can proxy the upstream Meldingen V2 API with a small allowlist of supported query parameters.
- A compatibility route can reuse that same fetch path and translate the response into the legacy V1 payload shape.
- Authentication concerns can be kept separate from the fetch routes so integration clients remain responsible for their own credentials and tokens.

At the moment, the PoC exposes these public endpoints:

- `POST /bearer-token`
- `GET /meldingen-v1`
- `GET /openapi`

## Findings during development

### 1. Authentication belongs at the integration boundary

The first version of the pull flow requested an OIDC token inside the shared fetch route. That coupled every downstream call to one authentication approach and made the route responsible for both transport logic and credential handling.

The current structure is cleaner:

- The shared fetch route expects the integration client to provide the `Authorization` header.
- The `/bearer-token` endpoint remains separate as a helper and local example, not as an implicit part of the pull route.
- The password grant helper no longer injects a configured username or password. The caller must submit those values explicitly.

That separation keeps the route behavior closer to production expectations, where integration partners usually handle their own token acquisition.

### 2. Keycloak and Entra ID are not drop-in equivalents

This backend does not only validate token signatures. It also expects a user-identifying claim and uses that claim to look up or create an application user.

- Local Keycloak is convenient for the PoC because the configured flow can return a user token with an email claim that already matches backend expectations.
- Production Entra ID often does not allow a simple username/password grant because of MFA, conditional access, or tenant policy.
- A client-credentials token is not equivalent to a user token here. App-only tokens usually identify the calling application rather than a human user.
- The token endpoint URL and requested scopes also differ between local Keycloak and a production Entra setup.

The main implication is that a production integration needs an explicit identity model. Camel must either act on behalf of a user or the backend must intentionally support app-only tokens.

### 3. Compatibility logic works best as a thin translation layer

The V1 compatibility path currently uses two small translation layers:

- `fetch-meldingen-v1.camel.yaml` keeps the public `/meldingen-v1` route and its internal upstream fetch route together in one place.
- `v1-state-filter-to-v2.ds` normalizes V1 and V2 state inputs before the upstream request is made.
- `meldingen-to-v1.ds` reshapes the V2 API payload into the legacy V1 response contract.

This keeps the compatibility logic outside the main API and avoids introducing municipality-specific legacy behavior into backend domain code.

There is a practical limitation as well: not every legacy V1 state has a clean V2 equivalent. Some states can be mapped directly, while others remain unmatched until a deliberate compatibility rule is added.

### 4. Keeping the integration assets separate from the API runtime is useful

The integration routes, filters, and transforms are optional deployment assets. They do not need to live inside the API application package or its runtime image.

Keeping them separate has a few benefits:

- The main API container stays focused on the backend application.
- Camel-specific configuration can evolve independently.
- Municipality-specific route behavior remains clearly separated from the shared API codebase.

## Possible next steps

The PoC is enough to validate the basic route shape, but a production-ready integration would still need more decisions and hardening.

The most relevant next steps are:

- Decide the production authentication model: delegated user tokens, an on-behalf-of flow, or backend changes to support app-only tokens deliberately.
- Add explicit validation and clear `400` responses on `/bearer-token` when required form fields such as `username` or `password` are missing for the selected grant type.
- Document the required `Authorization` header directly in the generated OpenAPI for `/meldingen-v1`.
- Add automated tests for the Camel routes and golden-file tests for the DataSonnet filters and transforms.
- Extend the compatibility layer only where real integration partners still need V1 semantics, for example additional query filters or response fields.
- Finalize the deployment story for Camel as a separate optional component, including route mounts, environment variables, and production-specific auth settings.

## Local-development assumptions

For local development, the PoC still assumes a seeded Keycloak realm and a development user such as `user@example.com` with password `password`. Those sample credentials are useful for local testing only and should not be treated as a production integration design.