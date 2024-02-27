from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from meldingen.api.v1.api import api_router
from meldingen.config import Settings
from meldingen.containers import Container


def get_application() -> FastAPI:
    container = Container()
    # TODO: We are currently unable to use `from_pydantic()`, because the `dependency-injector`
    # lacks support for pydantic v2.
    # https://python-dependency-injector.ets-labs.org/providers/configuration.html#loading-from-a-pydantic-settings
    container.settings.from_dict(Settings().model_dump())

    application = FastAPI(
        debug=container.settings.get("debug"),
        title=container.settings.get("project_name"),
        prefix=container.settings.get("url_prefix"),
    )
    application.container = container
    application.include_router(api_router)

    return application


app = get_application()


@app.middleware("http")
async def handle_resources(request: Request, call_next) -> Response:
    """Initialize dependency injection container resources before handling request
    and close them after handling the request.
    We need to do this in order for the resource dependencies to get "refreshed" every request."""

    await app.container.init_resources()

    response = await call_next(request)

    await app.container.shutdown_resources()

    return response
