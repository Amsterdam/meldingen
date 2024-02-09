from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
import sqlalchemy
from asgi_lifespan import LifespanManager
from dependency_injector import containers
from dependency_injector.providers import Object, Resource
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import Engine
from sqlmodel import Session

TEST_DATABASE_URL: str = "postgresql://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> Engine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return sqlalchemy.create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")


@pytest.fixture
def test_database(alembic_engine: Engine) -> None:
    from sqlmodel import SQLModel

    SQLModel.metadata.drop_all(alembic_engine)
    SQLModel.metadata.create_all(alembic_engine)


@pytest_asyncio.fixture
def app(test_database: None, alembic_engine: Engine) -> FastAPI:
    from main import get_application
    from meldingen.containers import Container

    def get_database_session(engine: Engine) -> Generator[Session, None, None]:
        session = Session(engine)
        yield session
        session.close()

    @containers.override(Container)
    class TestContainer(containers.DeclarativeContainer):
        database_engine: Object[Engine] = Object(alembic_engine)
        database_session: Resource[Session] = Resource(get_database_session, engine=database_engine)

    return get_application()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
