"""Local conftest for the LLM evaluation suite.

Silences DEBUG/INFO output from the HTTP and OpenAI client stacks so that when
a test fails, pytest's "Captured log call" section shows only what's actually
relevant — not several KB of httpcore connection trace lines.
"""

import logging

_NOISY_LOGGERS = (
    "asyncio",
    "httpcore",
    "httpcore.connection",
    "httpcore.http11",
    "httpx",
    "openai",
    "openai._base_client",
)

for _logger_name in _NOISY_LOGGERS:
    logging.getLogger(_logger_name).setLevel(logging.WARNING)
