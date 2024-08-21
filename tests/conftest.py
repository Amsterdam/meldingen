from typing import AsyncGenerator, AsyncIterator, Callable

import pytest
from asgi_lifespan import LifespanManager
from dependency_injector import containers
from dependency_injector.providers import Object, Resource
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest import FixtureRequest
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.sql.ddl import DropTable

from meldingen.containers import Container
from meldingen.database import DatabaseSessionManager
from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.main import get_application, get_container
from meldingen.models import BaseDBModel, User
from meldingen.repositories import UserRepository

TEST_DATABASE_URL: str = "postgresql+asyncpg://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
async def alembic_engine() -> AsyncIterator[AsyncEngine]:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    engine = create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        yield engine
    finally:
        await engine.dispose()


@compiles(DropTable, "postgresql")
def _compile_drop_table(element: DropTable, compiler: DDLCompiler) -> str:
    return compiler.visit_drop_table(element) + " CASCADE"


@pytest.fixture
async def test_database(alembic_engine: AsyncEngine) -> None:
    async with alembic_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.drop_all)
    async with alembic_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)


@pytest.fixture
def user_username(request: FixtureRequest) -> str:
    """Fixture providing a username."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "meldingen_user"


@pytest.fixture
def user_email(request: FixtureRequest) -> str:
    """Fixture providing a email."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "user@example.com"


@pytest.fixture
async def user(db_session: AsyncSession, user_username: str, user_email: str) -> User:
    user = User(username=user_username, email=user_email)

    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
async def users(db_session: AsyncSession) -> list[User]:
    """Fixture providing a list test user instances."""

    users = []
    for n in range(10):
        user = User(username=f"test_user_{n}", email=f"test_email_{n}@example.com")

        db_session.add(user)
        users.append(user)

    await db_session.commit()

    return users


@pytest.fixture
def container(alembic_engine: AsyncEngine) -> Container:
    async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            try:
                yield session
            except:
                await session.rollback()
                raise
            finally:
                await session.close()

    @containers.override(Container)
    class TestContainer(containers.DeclarativeContainer):
        database_engine: Object[AsyncEngine] = Object(alembic_engine)
        database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)

    return get_container()


@pytest.fixture
async def app(test_database: None, container: Container) -> FastAPI:
    return get_application(container)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client


@pytest.fixture
def db_engine() -> AsyncEngine:
    return create_async_engine(TEST_DATABASE_URL, echo="debug", poolclass=NullPool)


@pytest.fixture(autouse=True)
def database_engine_override(app: FastAPI) -> None:
    def db_engine_override() -> Callable[..., AsyncEngine]:
        return db_engine

    # In some case a coroutine is passed here instead of an FastAPI object, causing the test to fail
    if isinstance(app, FastAPI):
        app.dependency_overrides[database_engine] = db_engine_override


@pytest.fixture
def db_manager(db_engine: AsyncEngine) -> DatabaseSessionManager:
    return DatabaseSessionManager(db_engine)


@pytest.fixture(autouse=True)
def database_session_manager_override(app: FastAPI) -> None:
    def db_manager_override() -> Callable[..., DatabaseSessionManager]:
        return db_manager

    # In some case a coroutine is passed here instead of an FastAPI object, causing the test to fail
    if isinstance(app, FastAPI):
        app.dependency_overrides[database_session_manager] = db_manager_override


@pytest.fixture
async def db_session(db_manager: DatabaseSessionManager) -> AsyncIterator[AsyncSession]:
    async with db_manager.session() as session:
        try:
            await session.begin()
            yield session
        finally:
            await session.rollback()


@pytest.fixture(autouse=True)
async def session_override(app: FastAPI, db_session: AsyncSession) -> None:
    async def get_db_session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[database_session] = get_db_session_override


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
