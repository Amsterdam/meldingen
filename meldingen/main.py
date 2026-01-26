import logging
import os
from typing import Any

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.exc import IntegrityError
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_409_CONFLICT

from meldingen.api.v1.api import api_router
from meldingen.config import settings
from meldingen.middleware import ContentSizeLimitMiddleware


def get_application() -> FastAPI:
    application = FastAPI(
        debug=settings.debug,
        title=settings.project_name,
        prefix=settings.url_prefix,
        swagger_ui_init_oauth={
            "clientId": settings.auth_client_id,
            "scopes": settings.auth_scopes,
            "usePkceWithAuthorizationCodeGrant": True,
        },
        swagger_ui_parameters={"deepLinking": False},
        docs_url="/swagger",
    )
    application.include_router(api_router)

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


def add_custom_open_api_scheme(app: FastAPI) -> dict[str, Any]:

    # Cache
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2AuthorizationCodeBearer": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": settings.auth_url,
                    "tokenUrl": settings.token_url,
                    "x-scalar-client-id": settings.auth_client_id,
                    "scopes": {scope: "" for scope in settings.auth_scopes},
                }
            },
        }
    }
    openapi_schema["security"] = [{"OAuth2AuthorizationCodeBearer": []}]
    app.openapi_schema = openapi_schema

    return app.openapi_schema


app = get_application()
add_custom_open_api_scheme(app)

if os.getenv("CI") is None:
    # OpenTelemetry
    resource = Resource(attributes={SERVICE_NAME: settings.opentelemetry_service_name})
    # There can be only one tracer provider, and it cannot be changed after this, it will automatically be used
    # by all instrumentation
    tracer_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)

    logging_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

    logger = logging.getLogger()
    logger.addHandler(logging_handler)
    logger.setLevel(settings.log_level)

    AioHttpClientInstrumentor().instrument()

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    set_meter_provider(MeterProvider((metric_reader,)))

    FastAPIInstrumentor.instrument_app(app)
