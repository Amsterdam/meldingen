from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from fastapi import FastAPI
from pydantic import TypeAdapter

from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import (
    Classification,
    FormIoComponent,
    FormIoComponentTypeEnum,
    FormIoForm,
    FormIoFormDisplayEnum,
    FormIoPanelComponent,
    FormIoPrimaryForm,
    Melding,
    User,
)
from meldingen.repositories import ClassificationRepository, FormIoFormRepository, MeldingRepository, UserRepository


@pytest_asyncio.fixture
async def melding_repository(container: Container) -> MeldingRepository:
    return await container.melding_repository()


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


@pytest.fixture
def melding_token(request: SubRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)

    return None


@pytest.fixture
def melding_token_expires(request: SubRequest) -> datetime | None:
    if hasattr(request, "param"):
        timedelta_adapter = TypeAdapter(timedelta)
        return datetime.now() - timedelta_adapter.validate_python(request.param)

    return None


@pytest_asyncio.fixture
async def test_melding(
    melding_repository: MeldingRepository,
    melding_text: str,
    melding_state: str | None,
    melding_token: str | None,
    melding_token_expires: datetime | None,
) -> Melding:
    """Fixture providing a single test melding instance."""

    melding = Melding(text=melding_text)
    if melding_state is not None:
        melding.state = melding_state

    if melding_token is not None:
        melding.token = melding_token

    if melding_token_expires is not None:
        melding.token_expires = melding_token_expires

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
async def user_repository(container: Container) -> UserRepository:
    return await container.user_repository()


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
async def classification_repository(container: Container) -> ClassificationRepository:
    return await container.classification_repository()


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
async def form_repository(container: Container) -> FormIoFormRepository:
    return await container.form_repository()


@pytest_asyncio.fixture
async def primary_form(form_repository: FormIoFormRepository) -> FormIoPrimaryForm:
    primary_form = FormIoPrimaryForm(title="Primary Form", display=FormIoFormDisplayEnum.form, is_primary=True)

    component = FormIoComponent(
        label="klacht",
        description="Wat is uw klacht?",
        key="klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    components = await primary_form.awaitable_attrs.components
    components.append(component)

    await form_repository.save(primary_form)

    return primary_form


@pytest.fixture
def form_title(request: SubRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "Form"


@pytest_asyncio.fixture
async def form(form_repository: FormIoFormRepository, form_title: str) -> FormIoForm:
    form = FormIoForm(title=form_title, display=FormIoFormDisplayEnum.form)

    component = FormIoComponent(
        label="klacht",
        description="Wat is uw klacht?",
        key="klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    components = await form.awaitable_attrs.components
    components.append(component)

    await form_repository.save(form)

    return form


@pytest_asyncio.fixture
async def form_with_classification(
    classification_repository: ClassificationRepository, form_repository: FormIoFormRepository, form_title: str
) -> FormIoForm:
    classification = Classification("test_classification")
    await classification_repository.save(classification)
    form = FormIoForm(title=form_title, display=FormIoFormDisplayEnum.form, classification=classification)
    await form_repository.save(form)

    return form


@pytest_asyncio.fixture
async def test_forms(form_repository: FormIoFormRepository) -> list[FormIoForm]:
    forms = []
    for n in range(1, 11):
        form = FormIoForm(title=f"Form #{n}", display=FormIoFormDisplayEnum.form)

        await form_repository.save(form)

        forms.append(form)

    return forms
