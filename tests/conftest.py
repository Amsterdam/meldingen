from typing import AsyncGenerator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from dependency_injector import containers
from dependency_injector.providers import Object, Resource
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

TEST_DATABASE_URL: str = "postgresql+asyncpg://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> AsyncEngine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")


@pytest_asyncio.fixture
async def test_database(alembic_engine: AsyncEngine) -> None:
    from sqlmodel import SQLModel

    async with alembic_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


@pytest_asyncio.fixture
async def app(test_database: None, alembic_engine: AsyncEngine) -> FastAPI:
    from meldingen.containers import Container
    from meldingen.main import get_application

    async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session

    @containers.override(Container)
    class TestContainer(containers.DeclarativeContainer):
        database_engine: Object[AsyncEngine] = Object(alembic_engine)
        database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    return get_application()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
