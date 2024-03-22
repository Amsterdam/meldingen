import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from fastapi import FastAPI

from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import Classification, FormIoForm, FormIoFormDisplayEnum, FormIoPrimaryForm, Melding, User
from meldingen.repositories import ClassificationRepository, FormIoFormRepository, MeldingRepository, UserRepository


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


@pytest.fixture
def melding_state(request: SubRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return None


@pytest_asyncio.fixture
async def test_melding(melding_repository: MeldingRepository, melding_text: str, melding_state: str | None) -> Melding:
    """Fixture providing a single test melding instance."""

    melding = Melding(text=melding_text)
    if melding_state is not None:
        melding.state = melding_state

    await melding_repository.save(melding)

    return melding


@pytest_asyncio.fixture
async def test_meldingen(melding_repository: MeldingRepository, melding_text: str) -> list[Melding]:
    """Fixture providing a list test melding instances."""

    meldingen = []
    for _ in range(10):
        melding = Melding(text=melding_text)

        await melding_repository.save(melding)

        meldingen.append(melding)

    return meldingen


async def authenticate_user_override(token: str | None = None) -> User:
    user = User(username="user@example.com", email="user@example.com")
    user.id = 400
    return user


@pytest.fixture
def auth_user(app: FastAPI) -> None:
    app.dependency_overrides[authenticate_user] = authenticate_user_override


@pytest_asyncio.fixture
async def user_repository() -> UserRepository:
    """Fixture providing a UserRepository instance."""

    container = Container()
    user_repository = await container.user_repository()

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


@pytest_asyncio.fixture
async def classification_repository() -> ClassificationRepository:
    return await Container().classification_repository()


@pytest.fixture
def classification_name(request: SubRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "classification name"


@pytest_asyncio.fixture
async def classification(
    classification_repository: ClassificationRepository, classification_name: str
) -> Classification:
    classification = Classification(name=classification_name)

    await classification_repository.save(classification)

    return classification


@pytest_asyncio.fixture
async def classifications(classification_repository: ClassificationRepository) -> list[Classification]:
    classifications = []
    for n in range(10):
        classification = Classification(f"category: {n}")
        await classification_repository.save(classification)
        classifications.append(classification)

    return classifications


@pytest_asyncio.fixture
async def form_repository() -> FormIoFormRepository:
    """Fixture providing a FormIoFormRepository instance."""

    container = Container()
    _form_repository = await container.form_repository()

    return _form_repository


@pytest_asyncio.fixture
async def primary_form(form_repository: FormIoFormRepository) -> FormIoPrimaryForm:
    primary_form = FormIoPrimaryForm(title="Primary Form", display=FormIoFormDisplayEnum.form.value, is_primary=True)
    await form_repository.save(primary_form)

    return primary_form


@pytest_asyncio.fixture
async def form(form_repository: FormIoFormRepository) -> FormIoForm:
    primary_form = FormIoPrimaryForm(title="Form", display=FormIoFormDisplayEnum.form.value, is_primary=False)
    await form_repository.save(primary_form)

    return primary_form


@pytest_asyncio.fixture
async def test_forms(form_repository: FormIoFormRepository) -> list[FormIoForm]:
    forms = []
    for n in range(1, 11):
        form = FormIoForm(title=f"Form #{n}", display=FormIoFormDisplayEnum.form, is_primary=False)

        await form_repository.save(form)

        forms.append(form)

    return forms
