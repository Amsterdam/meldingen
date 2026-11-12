import asyncio
import functools
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest
from mypy_extensions import KwArg, VarArg

from meldingen.adapters.classification.dummy_classifier import DummyClassifierAdapter


@pytest.fixture(autouse=True)
def dummy_classifier(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value="Containers")
    monkeypatch.setattr(DummyClassifierAdapter, "__call__", mock)
    return mock


@pytest.fixture
def unclassifiable_classifier(dummy_classifier: AsyncMock) -> AsyncMock:
    dummy_classifier.return_value = "unclassifiable"
    return dummy_classifier


def async_step(step: Callable[[VarArg(Any), KwArg(Any)], Any]) -> Callable[[VarArg(Any), KwArg(Any)], Any]:
    """
    pytest-bdd doesn't offer a native way to run async steps, so we need to convert them to sync.
    https://github.com/pytest-dev/pytest-bdd/issues/223
    """

    @functools.wraps(step)
    def run_step(*args: list[Any], **kwargs: dict[Any, Any]) -> Any:
        try:
            """
            It is advised to use the following function to get the current loop.
            However this doesn't seem to find the current loop in the test environment.
            """
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            """
            We therefore fallback to this older function.
            If there is no event loop found, it will throw a Deprecation warning and create a
            a new event loop according to the current policy.
            This will become an error in a future version:
            https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
            """
            event_loop = asyncio.get_event_loop_policy().get_event_loop()
        return event_loop.run_until_complete(step(*args, **kwargs))

    return run_step
