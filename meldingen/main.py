import uuid
from importlib import metadata
from typing import Awaitable, Callable

import structlog
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_409_CONFLICT

from meldingen.api.v1.api import api_router
from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.utils import get_version


def get_container() -> Container:
    container = Container()
    # TODO: We are currently unable to use `from_pydantic()`, because the `dependency-injector`
    # lacks support for pydantic v2.
    # https://python-dependency-injector.ets-labs.org/providers/configuration.html#loading-from-a-pydantic-settings
    container.settings.from_dict(Settings().model_dump())

    return container


def get_application(cont: Container) -> FastAPI:
    application = FastAPI(
        debug=cont.settings.get("debug"),
        title=cont.settings.get("project_name"),
        prefix=cont.settings.get("url_prefix"),
    )
    application.include_router(api_router)

    @application.middleware("http")
    async def logging_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Middleware to log HTTP requests and responses. This middleware will
        add additional useful information to the log."""
        # Clear previous context variables
        structlog.contextvars.clear_contextvars()

        # Create a unique identifier for this request
        request_identifier = uuid.uuid4()

        # Bind useful contextvars
        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
            client_host=request.client.host if request.client else None,
            request_id=f"{request_identifier}",
            meldingen_version=get_version(),
            meldingen_core_version=metadata.version("meldingen-core"),
        )

        response = await call_next(request)

        # Bind the status code of the response to the contextvars
        structlog.contextvars.bind_contextvars(
            status_code=response.status_code,
        )

        if 400 <= response.status_code < 500:
            logger.warn("Client error")
        elif response.status_code >= 500:
            logger.error("Server error")
        else:
            logger.info("OK")

        return response

    @application.middleware("http")
    async def handle_resources(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Initialize dependency injection container resources before handling request
        and close them after handling the request.
        We need to do this in order for the resource dependencies to get "refreshed" every request."""

        await container.init_resources()

        response = await call_next(request)

        await container.shutdown_resources()

        return response

    @application.exception_handler(IntegrityError)
    async def sql_alchemy_integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_409_CONFLICT,
            content={"detail": "The requested operation could not be completed due to a conflict with existing data."},
        )

    return application


container = get_container()
app = get_application(container)

logger = structlog.get_logger()
