# Authentication

### Token Authentication while creating the signal
When creating a signal, the user is not logged in. We generate a unique token that is associated with that specific signal and store that in the user's cookies. This token is then used to authenticate requests related to that signal.

### OIDC
We use OpenID Connect (OIDC) for authentication on restricted endpoints, like the back-office or the admin endpoints. OIDC is an identity layer built on top of the OAuth 2.0 protocol, allowing clients to verify the identity of end-users based on the authentication performed by an authorization server.

In practice, that means that the front-end will send us an access token obtained from an OIDC provider (e.g., Keycloak, Entra ID) with each authorized request. We will then validate this token to ensure that the request is authenticated.

To validate this token, we use the `authenticate_user` function in `authentication.py`

### Using OIDC in your local environment

We need to configure the following environment variables for this to work properly:

- `API_AUTH_URL`: The URL of the OIDC provider's authorization endpoint.
- `API_TOKEN_URL`: The URL of the OIDC provider's token endpoint.
- `API_AUTH_CLIENT_ID`: The client ID registered with the OIDC provider.
- `API_AUTH_AUDIENCE`: The expected audience claim in the access token.
- `API_ISSUER_URL`: The expected issuer claim in the access token.
- `API_JWKS_URL`: The URL to fetch the JSON Web Key Set (JWKS) for token signature verification.
- `API_AUTH_SCOPES`: The scopes required for the access token.
- `API_AUTH_IDENTIFIER_FIELD`: The field in the token claims that uniquely identifies the user (e.g., "email" for their email address).

You may find examples of these fields for keycloak (`.env.example`) and Entra ID (`.env.example.entra`) in the repository. Both of these should work out of the box. All you need to do is copy them from the example to `.env`.

Lastly, you need to ensure that the user you login with is inserted into the database. For Keycloak, we use `user@example.com`, which is pre-created in the database migration. For Entra ID, you will need to create a user with the email you plan to use for logging in. For this, you can use the command `python main.py users add user@example.com`

### OIDC full flow

When the front-end also has a "server" component (e.g., Next.js), the full OIDC flow typically works as follows:

1. The user attempts to access a protected resource on the front-end application.
2. The front-end redirects the user to the OIDC provider's login page.
3. The user enters their credentials and logs in.
4. The OIDC provider authenticates the user and redirects them back to the front-end application
5. The front-end application receives an authorization code from the OIDC provider.
6. The front-end application exchanges the authorization code for an access token by making a request to the OIDC provider's token endpoint.
7. The front-end application includes the access token in the Authorization header of subsequent requests to the back-end API.
8. The back-end API validates the access token by checking its signature, expiration, and claims.
9. If the token is valid, the back-end API processes the request and returns the requested resource to the front-end application.
10. If the token is invalid or expired, the back-end API returns an unauthorized error, prompting the front-end application to redirect the user to the OIDC provider's login page again.

When the front-end is a pure client-side application (e.g., React, Angular), the flow is similar, but the front-end directly handles the token exchange and storage without a server component. Instead of a client secret, the front-end uses the PKCE (Proof Key for Code Exchange) extension to securely obtain the access token.

This is how PKCE works:

1. The user attempts to access a protected resource on the front-end application.
2. The front-end generates a code verifier (a random string) and derives a code challenge from it using a hashing algorithm.
3. The front-end redirects the user to the OIDC provider's login page, including the code challenge and the method used to derive it in the authorization request.
4. The user enters their credentials and logs in.
5. The OIDC provider authenticates the user and redirects them back to the front-end application
6. The front-end application receives an authorization code from the OIDC provider.
7. The front-end application exchanges the authorization code for an access token by making a request to the OIDC provider's token endpoint, including the code verifier in the request.
8. The OIDC provider validates the code verifier against the previously received code challenge. If they match, it issues an access token.
9. The front-end application includes the access token in the Authorization header of subsequent requests to the back-end API.
10. The back-end API validates the access token by checking its signature, expiration, and claims.
11. If the token is valid, the back-end API processes the request and returns the requested resource to the front-end application.
12. If the token is invalid or expired, the back-end API returns an unauthorized error, prompting the front-end application to redirect the user to the OIDC provider's login page again.


