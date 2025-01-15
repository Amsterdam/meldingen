from importlib import metadata
from typing import Awaitable, Callable

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.exc import IntegrityError
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_409_CONFLICT

from meldingen.api.v1.api import api_router
from meldingen.config import settings
from meldingen.logging import setup_logging
from meldingen.middleware import ContentSizeLimitMiddleware
from meldingen.utils import get_version


def get_application() -> FastAPI:
    application = FastAPI(
        debug=settings.debug,
        title=settings.project_name,
        prefix=settings.url_prefix,
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

    application.add_middleware(ContentSizeLimitMiddleware, max_size=settings.content_size_limit)
    application.add_middleware(CorrelationIdMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=["Content-Range"],
    )

    return application


app = get_application()

# OpenTelemetry
resource = Resource(attributes={SERVICE_NAME: settings.opentelemetry_service_name})
# There can be only one tracer provider, and it cannot be changed after this, it will automatically be used
# by all instrumentation
tracer_provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter())
tracer_provider.add_span_processor(processor)
trace.set_tracer_provider(tracer_provider)

FastAPIInstrumentor.instrument_app(app)

setup_logging()
logger = structlog.get_logger()
