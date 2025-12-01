from fastapi import APIRouter, Request
from scalar_fastapi import get_scalar_api_reference
from starlette.responses import HTMLResponse

router = APIRouter()


@router.get("/", include_in_schema=False, response_class=HTMLResponse, name="docs:scalar")
async def scalar_api_reference(request: Request) -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=request.app.openapi_url,
        title="Meldingen API Reference",
    )
