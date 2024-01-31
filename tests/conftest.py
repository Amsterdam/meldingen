from typing import AsyncGenerator, Generator

import alembic
import pytest
import pytest_asyncio
import sqlalchemy
from alembic.config import Config
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import Engine


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> Engine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return sqlalchemy.create_engine("postgresql://meldingen:postgres@database:5432/meldingen-test")


@pytest_asyncio.fixture(scope="session")
def apply_migrations() -> None:
    config = Config("alembic.ini")

    alembic.command.downgrade(config, "base")
    alembic.command.upgrade(config, "head")


@pytest_asyncio.fixture
def app(apply_migrations: None) -> FastAPI:
    from main import get_application

    return get_application()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
