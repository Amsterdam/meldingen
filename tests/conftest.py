from typing import AsyncGenerator, Annotated
from unittest.mock import Mock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager

# from dependency_injector import containers
# from dependency_injector.providers import Object, Resource
from fastapi import FastAPI, Depends
from httpx import AsyncClient
from jwt import PyJWKClient, PyJWT
from pytest import FixtureRequest
from pytest_alembic.config import Config as PytestAlembicConfig
from pytest_asyncio import is_async_test
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from meldingen.config import Settings
from meldingen.containers import get_database_engine, get_settings, get_database_session
from meldingen.main import get_application
from meldingen.models import BaseDBModel, User
from meldingen.repositories import UserRepository

TEST_DATABASE_URL: str = "postgresql+asyncpg://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> AsyncEngine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return create_async_engine(TEST_DATABASE_URL)


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


engine = None


def get_database_engine_override() -> AsyncEngine:
    global engine
    if engine is None:
        engine = create_async_engine(TEST_DATABASE_URL, echo="debug", poolclass=NullPool)
    return engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def database_engine() -> None:
    engine = get_database_engine_override()
    async with engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)

    print('HELLO: DB INIT')


session: AsyncSession | None = None
i = 0
async def get_database_session_override() -> AsyncGenerator[AsyncSession, None]:
    print("GET_DATABASE_SESSION_OVERRIDE")
    global i
    i = i + 1
    connection = None
    transaction = None

    global session
    if session is None:
        engine = get_database_engine_override()
        connection = await engine.connect()
        transaction = await connection.begin()

        async_session = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False,
                                           join_transaction_mode="create_savepoint")
        session = async_session()

    yield session
    print(f"I: {i}")

    if session is not None and i == 1:
        i = 0
        print('TRANS ROLLBACK')
        await session.close()
        session = None
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def database_session() -> AsyncSession:
    yield from get_database_session_override()


@pytest_asyncio.fixture
async def app() -> FastAPI:
    global session
    session = None
    settings = Settings()
    app = get_application(settings.model_dump())
    # app.dependency_overrides[get_database_engine] = get_database_engine_override
    app.dependency_overrides[get_database_session] = get_database_session_override

    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    # async with LifespanManager(app):
    async with AsyncClient(
        app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
    ) as client:
        yield client
