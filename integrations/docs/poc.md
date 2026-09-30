# Camel Integration PoC

This document captures what the Camel-based integration proof of concept is meant to demonstrate, what was learned during implementation, and what follow-up work would make it more production-shaped.

## What this PoC covers

The current PoC demonstrates four core ideas:

- Camel can sit next to the Meldingen API as an optional integration component rather than pushing municipality-specific logic into the backend.
- A shared internal fetch route can proxy the upstream Meldingen V2 API with a small allowlist of supported query parameters.
- A compatibility route can reuse that same fetch path and translate the response into the legacy V1 payload shape.
- A way to detect changes in the API endpoints that might concern the integration layer

At the moment, the PoC exposes these public endpoints:

- `POST /bearer-token`
- `GET /meldingen-v1`
- `GET /openapi`

## Findings during development

### 1. Keycloak and Entra ID are not drop-in equivalents

The created auth.yaml works with the local Keycloak, but it might not work with Entra ID. It is still unclear how the client connections to Entra ID should work.

### 2. DataSonnet

DataSonnet works well in this case, because it is a flexible language natively supported by Camel. It supports different language types such as XML (for THOR) and JSON. It also has modules built in so that we can import functionality (such as the one the lib folder) to other documents.


## Possible improvements

- Make the Integration Layer OpenAPI spec viewable through something like Swagger or Scalar
- Add automated tests for the Camel routes and golden-file tests for the DataSonnet filters and transforms. This could help with keeping the integration and API code in sync.
