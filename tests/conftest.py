from typing import AsyncGenerator
from unittest.mock import Mock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from dependency_injector import containers
from dependency_injector.providers import Object, Resource
from fastapi import FastAPI
from httpx import AsyncClient
from jwt import PyJWKClient, PyJWT
from pytest import FixtureRequest
from pytest_alembic.config import Config as PytestAlembicConfig
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import DDLCompiler
from sqlalchemy.sql.ddl import DropTable

from meldingen.containers import Container
from meldingen.main import get_application, get_container
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
    return create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")


@compiles(DropTable, "postgresql")
def _compile_drop_table(element: DropTable, compiler: DDLCompiler) -> str:
    return compiler.visit_drop_table(element) + " CASCADE"


@pytest_asyncio.fixture
async def test_database(alembic_engine: AsyncEngine) -> None:
    async with alembic_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.drop_all)
    async with alembic_engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)


@pytest.fixture
def jwks_client_mock() -> PyJWKClient:
    return Mock(PyJWKClient)


@pytest.fixture
def py_jwt_mock() -> PyJWT:
    return Mock(PyJWT)


@pytest_asyncio.fixture
async def user_repository(container: Container) -> UserRepository:
    return await container.user_repository()


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


@pytest_asyncio.fixture
async def test_user(user_repository: UserRepository, user_username: str, user_email: str) -> User:
    """Fixture providing a single test user instance."""

    user = User(username=user_username, email=user_email)

    await user_repository.save(user)

    return user


@pytest_asyncio.fixture
async def test_users(user_repository: UserRepository) -> list[User]:
    """Fixture providing a list test user instances."""

    users = []
    for n in range(10):
        user = User(username=f"test_user_{n}", email=f"test_email_{n}@example.com")

        await user_repository.save(user)

        users.append(user)

    return users


@pytest.fixture
def container(alembic_engine: AsyncEngine, jwks_client_mock: PyJWKClient, py_jwt_mock: PyJWT) -> Container:
    async def get_database_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            yield session

    @containers.override(Container)
    class TestContainer(containers.DeclarativeContainer):
        database_engine: Object[AsyncEngine] = Object(alembic_engine)
        database_session: Resource[AsyncSession] = Resource(get_database_session, engine=database_engine)
        jwks_client: Object[PyJWKClient] = Object(jwks_client_mock)
        py_jwt: Object[PyJWT] = Object(py_jwt_mock)

    return get_container()


@pytest_asyncio.fixture
async def app(test_database: None, container: Container) -> FastAPI:
    return get_application(container)


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app, base_url="http://testserver", headers={"Content-Type": "application/json"}
        ) as client:
            yield client
