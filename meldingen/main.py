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

from meldingen.config import settings

from meldingen.logging import setup_logging
from meldingen.utils import get_version


def get_application(settings: dict) -> FastAPI:
    application = FastAPI(
        debug=settings.get("debug"),
        title=settings.get("project_name"),
        prefix=settings.get("url_prefix"),
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

    @application.exception_handler(IntegrityError)
    async def sql_alchemy_integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_409_CONFLICT,
            content={"detail": "The requested operation could not be completed due to a conflict with existing data."},
        )

    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get("cors_allow_origins"),
        allow_credentials=settings.get("cors_allow_credentials"),
        allow_methods=settings.get("cors_allow_methods"),
        allow_headers=settings.get("cors_allow_headers"),
        expose_headers=["Content-Range"],
    )

    return application


app = get_application(settings.model_dump())

setup_logging()
logger = structlog.get_logger()
