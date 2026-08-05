from fastapi import APIRouter, Request
from scalar_fastapi import get_scalar_api_reference
from starlette.responses import HTMLResponse

from meldingen.config import settings

router = APIRouter()

# scalar-fastapi defaults to the unversioned CDN URL
# (https://cdn.jsdelivr.net/npm/@scalar/api-reference), which jsDelivr resolves to
# whatever is `latest` at page load. That means the docs page silently upgrades its
# own frontend without a deploy, and a Scalar release can break OAuth here with no
# change on our side. It already did: newer builds stopped honouring the
# `selectedScopes` below, so scopes had to be ticked by hand on every login
# (https://github.com/scalar/scalar/issues/8084).
#
# 1.43.15 is the version that was `latest` when the OAuth config below was finished
# and verified. Before bumping, re-check that the scopes come pre-selected.
SCALAR_JS_URL = "https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.43.15"


@router.get("/", include_in_schema=True, response_class=HTMLResponse, name="docs:scalar")
async def scalar_api_reference(request: Request) -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=request.app.openapi_url,
        title="Meldingen API Reference",
        scalar_js_url=SCALAR_JS_URL,
        authentication={
            "preferredSecurityScheme": "OAuth2AuthorizationCodeBearer",
            "securitySchemes": {
                "OAuth2AuthorizationCodeBearer": {
                    "flows": {
                        "authorizationCode": {
                            "x-scalar-client-id": settings.auth_client_id,
                            "selectedScopes": settings.auth_scopes,
                            "x-usePkce": "SHA-256",
                            "x-scalar-redirect-uri": f"{request.base_url}docs/oauth2-redirect",
                            "x-scalar-security-body": {
                                "client_id": settings.auth_client_id,
                            },
                        }
                    }
                }
            },
        },
    )
