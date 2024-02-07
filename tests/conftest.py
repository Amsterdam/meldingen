from typing import AsyncGenerator

import alembic
import pytest
import pytest_asyncio
import sqlalchemy
from alembic.command import downgrade, upgrade
from alembic.config import Config
from asgi_lifespan import LifespanManager
from dependency_injector import containers
from dependency_injector.providers import Object
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import Engine

TEST_DATABASE_URL: str = "postgresql://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> Engine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return sqlalchemy.create_engine(TEST_DATABASE_URL)


@pytest_asyncio.fixture(scope="session")
def apply_migrations() -> None:
    config = Config("alembic.ini")

    downgrade(config, "base")
    upgrade(config, "head")


@pytest_asyncio.fixture
def app(apply_migrations: None, alembic_engine: Engine) -> FastAPI:
    from main import get_application
    from meldingen.containers import Container

    @containers.override(Container)
    class TestContainer(containers.DeclarativeContainer):
        database_engine: Object[Engine] = Object(alembic_engine)

    return get_application()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
