import logging

import uvicorn
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
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

logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
set_logger_provider(logger_provider)

logging_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(settings.log_level)

AioHttpClientInstrumentor().instrument()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
