import asyncio
import functools

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from meldingen.dependencies import database_session, database_session_manager, database_engine
from tests.conftest import test_database
from typing import Callable, AsyncIterator, AsyncGenerator
from meldingen.database import DatabaseSessionManager

def async_to_sync(step):
    """
    pytest-bdd doesn't offer a native way to run async steps, so we need to convert them to sync.
    https://github.com/pytest-dev/pytest-bdd/issues/223
    """

    @functools.wraps(step)
    def run_step(*args, **kwargs):
        try:
            """
            It is advised to use the following function to get the current loop. 
            However this doesn't seem to find the current loop in the test environment.
            """
            event_loop = asyncio.get_running_loop()
            print('got event loop from get_running_loop')
        except RuntimeError:
            """
            We therefore fallback to this older function.
            If there is no event loop found, it will throw a Deprecation warning and create a 
            a new event loop according to the current policy. 
            This will become an error in a future version: 
            https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
            """
            event_loop = asyncio.get_event_loop_policy().get_event_loop()
            print('got event loop from get_event_loop')
        return event_loop.run_until_complete(step(*args, **kwargs))

    return run_step


