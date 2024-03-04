import logging
import sys

import structlog
from asgi_correlation_id import correlation_id
from structlog.typing import EventDict, Processor, WrappedLogger

from meldingen.config import settings


def _add_correlation(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add the request id to the EventDict."""
    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging() -> None:
    # Disable uvicorn logging
    logging.getLogger("uvicorn.error").disabled = True
    logging.getLogger("uvicorn.access").disabled = True

    # The log level, will be set to DEBUG if the debug setting is set to true
    # otherwise the log_level setting is used.
    log_level = logging.DEBUG if settings.debug else settings.log_level

    # Standard logging configuration
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    log_renderer = structlog.dev.ConsoleRenderer()

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_correlation,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_log_level_number,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.dev.set_exc_info,
        log_renderer,
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
