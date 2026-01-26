from fastapi import APIRouter, Request
from scalar_fastapi import get_scalar_api_reference
from starlette.responses import HTMLResponse

from meldingen.config import settings

router = APIRouter()


@router.get("/", include_in_schema=True, response_class=HTMLResponse, name="docs:scalar")
async def scalar_api_reference(request: Request) -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=request.app.openapi_url,
        title="Meldingen API Reference",
        authentication={
            "preferredSecurityScheme": "OAuth2AuthorizationCodeBearer",
            "securitySchemes": {
                "OAuth2AuthorizationCodeBearer": {
                    "flows": {
                        "authorizationCode": {
                            "x-scalar-client-id": settings.auth_client_id,
                            "selectedScopes": settings.auth_scopes,
                            # "x-usePkce": "SHA-256",
                            "x-scalar-redirect-uri": f"{request.base_url}docs/oauth2-redirect",
                            'x-scalar-credentials-location': 'body'
                        }
                    }
                }
            },
        },
    )
