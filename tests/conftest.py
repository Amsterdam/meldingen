import contextlib
from typing import AsyncGenerator, AsyncIterator, Callable

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest import FixtureRequest
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.sql.ddl import DropTable

from meldingen.database import DatabaseSessionManager as BaseDatabaseSessionManager
from meldingen.dependencies import database_engine, database_session, database_session_manager
from meldingen.main import get_application
from meldingen.models import BaseDBModel, User

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


@pytest.fixture(scope="session", autouse=True)
async def test_database(anyio_backend: str, db_engine: AsyncEngine) -> None:
    async with db_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.drop_all)
    async with db_engine.begin() as conn:
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
async def app() -> FastAPI:
    return get_application()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
            headers={"Content-Type": "application/json"},
        ) as client:
            yield client


@pytest.fixture(scope="session")
def db_engine() -> AsyncEngine:
    return create_async_engine(TEST_DATABASE_URL, echo="debug", poolclass=NullPool)


@pytest.fixture(autouse=True)
def database_engine_override(app: FastAPI) -> None:
    def db_engine_override() -> Callable[..., AsyncEngine]:
        return db_engine

    # In some case a coroutine is passed here instead of an FastAPI object, causing the test to fail
    if isinstance(app, FastAPI):
        app.dependency_overrides[database_engine] = db_engine_override


class DatabaseSessionManager(BaseDatabaseSessionManager):
    _engine: AsyncEngine

    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        connection = await self._engine.connect()
        transaction = await connection.begin()
        sessionmaker = async_sessionmaker(
            autocommit=False, bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        session = sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await transaction.rollback()
            await connection.close()


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


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
