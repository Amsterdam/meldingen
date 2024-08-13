from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from meldingen_core.exceptions import NotFoundException
from pydantic import TypeAdapter
from pytest import FixtureRequest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.authentication import authenticate_user
from meldingen.containers import Container
from meldingen.models import (
    Classification,
    Form,
    FormIoComponentTypeEnum,
    FormIoFormDisplayEnum,
    FormIoPanelComponent,
    FormIoTextAreaComponent,
    Melding,
    Question,
    StaticForm,
    StaticFormTypeEnum,
    User,
)
from meldingen.repositories import ClassificationRepository, FormRepository, QuestionRepository


@pytest.fixture
def melding_text(request: FixtureRequest) -> str:
    """Fixture providing a test melding text."""

    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "This is a test melding."


@pytest.fixture
def melding_state(request: FixtureRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return None


@pytest.fixture
def melding_token(request: FixtureRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)

    return None


@pytest.fixture
def melding_token_expires(request: FixtureRequest) -> datetime | None:
    if hasattr(request, "param"):
        timedelta_adapter = TypeAdapter(timedelta)
        return datetime.now() - timedelta_adapter.validate_python(request.param)

    return None


@pytest.fixture
async def melding(
    db_session: AsyncSession,
    melding_text: str,
    melding_state: str | None,
    melding_token: str | None,
    melding_token_expires: datetime | None,
) -> Melding:
    melding = Melding(text=melding_text)
    if melding_state is not None:
        melding.state = melding_state

    if melding_token is not None:
        melding.token = melding_token

    if melding_token_expires is not None:
        melding.token_expires = melding_token_expires

    db_session.add(melding)
    await db_session.commit()

    return melding


@pytest.fixture
async def melding_with_classification(
    db_session: AsyncSession,
    melding: Melding,
    test_classification: Classification,
) -> Melding:
    melding.classification = test_classification

    db_session.add(melding)
    await db_session.commit()

    return melding


@pytest.fixture
async def meldingen(db_session: AsyncSession, melding_text: str) -> list[Melding]:
    meldingen = []
    for i in range(10):
        melding = Melding(text=f"{melding_text} {i}")

        db_session.add(melding)
        meldingen.append(melding)

    await db_session.commit()

    return meldingen


async def authenticate_user_override(token: str | None = None) -> User:
    user = User(username="user@example.com", email="user@example.com")
    user.id = 400
    return user


@pytest.fixture
def auth_user(app: FastAPI) -> None:
    app.dependency_overrides[authenticate_user] = authenticate_user_override


@pytest.fixture
def classification_name(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "classification name"


@pytest.fixture
async def classification(
    classification_repository: ClassificationRepository, classification_name: str
) -> Classification:
    try:
        classification = await classification_repository.find_by_name(classification_name)
    except NotFoundException:
        classification = Classification(name=classification_name)
        await classification_repository.save(classification)

    return classification


@pytest.fixture
async def test_classification(db_session: AsyncSession, classification_name: str) -> Classification:
    classification = Classification(name=classification_name)
    db_session.add(classification)
    await db_session.commit()

    return classification


@pytest.fixture
async def classifications(db_session: AsyncSession) -> list[Classification]:
    classifications = []
    for n in range(10):
        classification = Classification(f"category: {n}")
        db_session.add(classification)
        classifications.append(classification)

    await db_session.commit()

    return classifications


@pytest.fixture
async def classification_with_form(db_session: AsyncSession) -> Classification:
    classification = Classification("test_classification")
    form = Form(title="test_form", display=FormIoFormDisplayEnum.form, classification=classification)

    db_session.add(form)
    await db_session.commit()

    return classification


@pytest.fixture
async def form_repository(container: Container) -> FormRepository:
    return await container.form_repository()


@pytest.fixture
def form_title(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "Form"


@pytest.fixture
async def form(form_repository: FormRepository, question_repository: QuestionRepository, form_title: str) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    components = await form.awaitable_attrs.components
    components.append(component)

    await form_repository.save(form)

    question = Question(text=component.description, form=form)

    await question_repository.save(question)

    component.question = question

    await form_repository.save(form)

    return form


@pytest.fixture
async def test_form(db_session: AsyncSession, form_title: str) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    components = await form.awaitable_attrs.components
    components.append(component)

    question = Question(text=component.description, form=form)

    component.question = question

    db_session.add(form)
    await db_session.commit()

    return form


@pytest.fixture
async def form_with_classification(
    classification_repository: ClassificationRepository,
    form_repository: FormRepository,
    question_repository: QuestionRepository,
    form_title: str,
) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    panel = FormIoPanelComponent(
        label="Page 1",
        key="page1",
        input=False,
        type=FormIoComponentTypeEnum.panel,
    )

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    panel_components = await panel.awaitable_attrs.components
    panel_components.append(component)

    components = await form.awaitable_attrs.components
    components.append(panel)

    await form_repository.save(form)

    question = Question(text=component.description, form=form)

    await question_repository.save(question)

    component.question = question

    try:
        classification = await classification_repository.find_by_name("test_classification")
    except NotFoundException:
        classification = Classification("test_classification")
        await classification_repository.save(classification)

    form.classification = classification
    await form_repository.save(form)

    return form


@pytest.fixture
async def test_form_with_classification(db_session: AsyncSession, form_title: str) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    panel = FormIoPanelComponent(
        label="Page 1",
        key="page1",
        input=False,
        type=FormIoComponentTypeEnum.panel,
    )

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        show_char_count=True,
    )

    panel_components = await panel.awaitable_attrs.components
    panel_components.append(component)

    components = await form.awaitable_attrs.components
    components.append(panel)

    question = Question(text=component.description, form=form)

    db_session.add(question)

    component.question = question

    result = await db_session.execute(select(Classification).where(Classification.name == "test_classification"))
    classification = result.scalars().one_or_none()
    if classification is None:
        classification = Classification("test_classification")
        db_session.add(classification)

    form.classification = classification
    db_session.add(form)

    await db_session.commit()

    return form


@pytest.fixture
async def forms(db_session: AsyncSession) -> list[Form]:
    forms = []
    for n in range(1, 11):
        form = Form(title=f"Form #{n}", display=FormIoFormDisplayEnum.form)

        db_session.add(form)

        forms.append(form)

    await db_session.commit()

    return forms


@pytest.fixture
async def primary_form(db_session: AsyncSession) -> StaticForm:
    try:
        statement = select(StaticForm).where(StaticForm.type == StaticFormTypeEnum.primary)

        result = await db_session.execute(statement)
        primary_form = result.scalars().one()
    except NoResultFound:
        primary_form = StaticForm(
            type=StaticFormTypeEnum.primary, title="Primary form", display=FormIoFormDisplayEnum.form
        )

        component = FormIoTextAreaComponent(
            label="Waar gaat het om?",
            description="",
            key="waar-gaat-het-om",
            type=FormIoComponentTypeEnum.text_area,
            input=True,
            auto_expand=True,
            show_char_count=True,
        )

        components = await primary_form.awaitable_attrs.components
        components.append(component)

        db_session.add(primary_form)
        await db_session.commit()

    return primary_form
