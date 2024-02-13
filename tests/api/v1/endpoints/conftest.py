import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from fastapi import FastAPI

from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Melding, User
from meldingen.repositories import MeldingRepository


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
