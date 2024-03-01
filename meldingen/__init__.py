import logging
import sys

import structlog

from meldingen.config import settings

log = structlog.get_logger()

# Disable uvicorn logging
logging.getLogger("uvicorn.error").disabled = True
logging.getLogger("uvicorn.access").disabled = True

# The log level, will be set to DEBUG if the debug setting is set to true
# otherwise the log_level setting is used.
log_level = logging.DEBUG if settings.debug else settings.log_level

# Standard logging configuration
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

# Structlog configuration
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
