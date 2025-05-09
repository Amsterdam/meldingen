import contextlib
from typing import AsyncGenerator, AsyncIterator
from unittest.mock import AsyncMock, Mock

import pytest
from _pytest.tmpdir import TempPathFactory
from asgi_lifespan import LifespanManager
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import ContainerClient
from fastapi import FastAPI
from filelock import FileLock
from httpx import ASGITransport, AsyncClient
from meldingen_core.malware import BaseMalwareScanner
from pytest import FixtureRequest
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.sql.ddl import DropTable

from meldingen.config import settings
from meldingen.database import DatabaseSessionManager as BaseDatabaseSessionManager
from meldingen.dependencies import (
    azure_container_client,
    database_engine,
    database_session,
    database_session_manager,
    malware_scanner,
    public_id_generator,
)
from meldingen.generators import PublicIdGenerator
from meldingen.main import get_application
from meldingen.models import BaseDBModel, User

pytest_plugins = ["mailpit.testing.pytest"]
TEST_DATABASE_URL: str = "postgresql+asyncpg://meldingen:postgres@database:5432/meldingen-test"


@pytest.fixture
def alembic_config() -> PytestAlembicConfig:
    """Override this fixture to configure the exact alembic context setup required."""
    return PytestAlembicConfig()


@pytest.fixture
def alembic_engine() -> AsyncEngine:
    """Override this fixture to provide pytest-alembic powered tests with a database handle."""
    return create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")


@compiles(DropTable, "postgresql")
def _compile_drop_table(element: DropTable, compiler: DDLCompiler) -> str:
    return compiler.visit_drop_table(element) + " CASCADE"


async def setup_database(db_engine: AsyncEngine) -> None:
    async with db_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.drop_all)
    async with db_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)


@pytest.fixture(scope="session")
async def test_database(
    anyio_backend: str, db_engine: AsyncEngine, worker_id: str, tmp_path_factory: TempPathFactory
) -> None:
    """Based on example:
    https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once"""

    if worker_id == "master":
        await setup_database(db_engine)
        return

    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    file_path = root_tmp_dir / "test.db"
    with FileLock(str(file_path) + ".lock"):
        if file_path.is_file():
            return

        await setup_database(db_engine)
        file_path.write_text("created")


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
def app() -> FastAPI:
    return get_application()


@pytest.fixture
async def client(app: FastAPI, test_database: None) -> AsyncGenerator[AsyncClient, None]:
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


@pytest.fixture
async def db_session(db_manager: DatabaseSessionManager) -> AsyncIterator[AsyncSession]:
    async with db_manager.session() as session:
        try:
            await session.begin()
            yield session
        finally:
            await session.rollback()


@pytest.fixture(autouse=True)
async def override_dependencies(
    app: FastAPI, db_engine: AsyncEngine, db_manager: DatabaseSessionManager, db_session: AsyncSession
) -> AsyncIterator[None]:

    async def db_session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    def db_engine_override() -> AsyncEngine:
        return db_engine

    def db_manager_override() -> DatabaseSessionManager:
        return db_manager

    app.dependency_overrides.update(
        {
            database_session: db_session_override,
            database_engine: db_engine_override,
            database_session_manager: db_manager_override,
        }
    )

    yield

    app.dependency_overrides.clear()


async def init_storage(client: ContainerClient) -> None:
    try:
        await client.delete_container()
    except ResourceNotFoundError:
        """No need to delete the container if it does not exist."""

    await client.create_container()


@pytest.fixture
async def container_client(tmp_path_factory: TempPathFactory, worker_id: str) -> AsyncIterator[ContainerClient]:
    """Based on example:
    https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once"""

    client = ContainerClient.from_connection_string(
        settings.azure_storage_connection_string, settings.azure_storage_container
    )

    async with client:
        if worker_id == "master":
            await init_storage(client)

        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        file_path = root_tmp_dir / "test.storage"
        with FileLock(str(file_path) + ".lock"):
            if not file_path.is_file():
                await init_storage(client)
                file_path.write_text("inited")

            yield client


@pytest.fixture(autouse=True)
def azure_container_client_override(app: FastAPI, container_client: ContainerClient) -> None:
    async def get_azure_container_client() -> AsyncIterator[ContainerClient]:
        yield container_client

    # In some case a coroutine is passed here instead of an FastAPI object, causing the test to fail
    if isinstance(app, FastAPI):
        app.dependency_overrides[azure_container_client] = get_azure_container_client


@pytest.fixture
def malware_scanner_override(app: FastAPI) -> None:
    scanner = AsyncMock(BaseMalwareScanner)

    def test_malware_scanner() -> BaseMalwareScanner:
        return scanner

    app.dependency_overrides[malware_scanner] = test_malware_scanner


@pytest.fixture
def public_id_generator_override(app: FastAPI) -> None:
    generator = Mock(PublicIdGenerator)
    generator.side_effect = ["PUBMEL", "MELPUB"]

    def test_public_id_generator() -> PublicIdGenerator:
        return generator

    app.dependency_overrides[public_id_generator] = test_public_id_generator


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
