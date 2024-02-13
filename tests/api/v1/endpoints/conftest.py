import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from fastapi import FastAPI

from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Melding, User
from meldingen.repositories import MeldingRepository, UserRepository


@pytest_asyncio.fixture
async def melding_repository() -> MeldingRepository:
    """Fixture providing a MeldingRepository instance."""

    container = Container()
    melding_repository = await container.melding_repository()

    return melding_repository


@pytest.fixture
def melding_text(request: SubRequest) -> str:
    """Fixture providing a test melding text."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "This is a test melding."


@pytest_asyncio.fixture
async def test_melding(melding_repository: MeldingRepository, melding_text: str) -> Melding:
    """Fixture providing a single test melding instance."""

    melding = Melding()
    melding.text = melding_text

    await melding_repository.add(melding)

    return melding


@pytest_asyncio.fixture
async def test_meldingen(melding_repository: MeldingRepository, melding_text: str) -> list[Melding]:
    """Fixture providing a list test melding instances."""

    meldingen = []
    for _ in range(10):
        melding = Melding()
        melding.text = melding_text

        await melding_repository.add(melding)

        meldingen.append(melding)

    return meldingen


async def authenticate_user_override(token: str | None = None) -> User:
    return User(username="user@example.com", email="user@example.com")


@pytest.fixture
def auth_user(app: FastAPI) -> None:
    app.dependency_overrides[authenticate_user] = authenticate_user_override


@pytest.fixture
def user_repository() -> UserRepository:
    """Fixture providing a UserRepository instance."""

    container = Container()
    user_repository = container.user_repository()

    return user_repository


@pytest.fixture
def user_username(request: SubRequest) -> str:
    """Fixture providing a username."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "meldingen_user"


@pytest.fixture
def user_email(request: SubRequest) -> str:
    """Fixture providing a email."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "user@example.com"


@pytest.fixture
def test_user(user_repository: UserRepository, user_username: str, user_email: str) -> User:
    """Fixture providing a single test user instance."""

    user = User()
    user.username = user_username
    user.email = user_email

    user_repository.add(user)

    return user


@pytest.fixture
def test_users(user_repository: UserRepository) -> list[User]:
    """Fixture providing a list test user instances."""

    users = []
    for n in range(10):
        user = User()
        user.username = f"test_user_{n}"
        user.email = f"test_email_{n}@example.com"

        user_repository.add(user)

        users.append(user)

    return users
