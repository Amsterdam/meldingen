from contextlib import asynccontextmanager
from importlib import metadata
from typing import Awaitable, Callable

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_409_CONFLICT

from meldingen.api.v1.api import api_router
from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.database import sessionmanager
from meldingen.logging import setup_logging
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

        # Bind useful contextvars
        structlog.contextvars.bind_contextvars(
            path=request.url.path,
            method=request.method,
            client_host=request.client.host if request.client else None,
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
        and close them after handling the request. We also reset Singletons.
        We need to do this in order for the resource dependencies to get "refreshed" every request."""

        container.reset_singletons()
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

    application.add_middleware(CorrelationIdMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cont.settings.get("cors_allow_origins"),
        allow_credentials=cont.settings.get("cors_allow_credentials"),
        allow_methods=cont.settings.get("cors_allow_methods"),
        allow_headers=cont.settings.get("cors_allow_headers"),
        expose_headers=["Content-Range"],
    )

    return application


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Function that handles startup and shutdown events.
    See also https://fastapi.tiangolo.com/advanced/events/"""
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


container = get_container()
app = get_application(container)

setup_logging()
logger = structlog.get_logger()
