from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from pydantic import TypeAdapter
from pytest import FixtureRequest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.authentication import authenticate_user
from meldingen.models import (
    Answer,
    Attachment,
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
def melding_geo_location(request: FixtureRequest) -> str | None:
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
def melding_email(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
def melding_phone(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
async def melding(
    db_session: AsyncSession,
    melding_text: str,
    melding_state: str | None,
    melding_token: str | None,
    melding_token_expires: datetime | None,
    melding_geo_location: str | None,
    melding_email: str | None,
    melding_phone: str | None,
) -> Melding:
    melding = Melding(text=melding_text)
    if melding_state is not None:
        melding.state = melding_state

    if melding_token is not None:
        melding.token = melding_token

    if melding_token_expires is not None:
        melding.token_expires = melding_token_expires

    if melding_geo_location is not None:
        melding.geo_location = melding_geo_location

    melding.email = melding_email
    melding.phone = melding_phone

    db_session.add(melding)
    await db_session.commit()

    return melding


@pytest.fixture
async def melding_with_classification(
    db_session: AsyncSession,
    melding: Melding,
    classification: Classification,
) -> Melding:
    melding.classification = classification

    db_session.add(melding)
    await db_session.commit()

    return melding


@pytest.fixture
async def form_with_multiple_questions(
    db_session: AsyncSession, melding_with_classification: Melding, classification: Classification, is_required: bool
) -> Form:
    form = Form(title="Form", classification=classification)
    questions = []
    for i in range(10):
        question = Question(text=f"Question {i}")
        questions.append(question)
        panel = FormIoPanelComponent(label=f"Panel {i}", key=f"Panel Key {i}", type="panel")
        component = FormIoTextAreaComponent(label=f"Component {i}", key=f"Key {i}")
        component.question = question
        component.parent = panel
        component.required = is_required

        form.components.append(panel)

    form.components.reorder()
    form.questions = questions
    db_session.add(form)

    await db_session.commit()

    return form


@pytest.fixture
async def melding_with_answers(
    db_session: AsyncSession, melding_with_classification: Melding, form_with_multiple_questions: Form
) -> Melding:
    questions = await form_with_multiple_questions.awaitable_attrs.questions

    numbers = [6, 3, 2, 9, 7, 1, 8, 4, 5, 0]
    for i in numbers:
        db_session.add(
            Answer(
                text=f"Answer {i}",
                melding=melding_with_classification,
                question=questions[i],
            )
        )

    await db_session.commit()

    return melding_with_classification


@pytest.fixture
async def melding_with_some_answers(
    db_session: AsyncSession, melding_with_classification: Melding, form_with_multiple_questions: Form
) -> Melding:
    questions = await form_with_multiple_questions.awaitable_attrs.questions

    numbers = [6, 3, 2, 9, 7]
    for i in numbers:
        db_session.add(
            Answer(
                text=f"Answer {i}",
                melding=melding_with_classification,
                question=questions[i],
            )
        )

    await db_session.commit()

    return melding_with_classification


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
async def classification(db_session: AsyncSession, classification_name: str) -> Classification:
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
def form_title(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return "Form"


@pytest.fixture
def is_required(request: FixtureRequest) -> bool:
    if hasattr(request, "param"):
        return bool(request.param)
    else:
        return False


@pytest.fixture
async def form(db_session: AsyncSession, form_title: str) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        max_char_count=255,
    )

    components = await form.awaitable_attrs.components
    components.append(component)

    question = Question(text=component.description, form=form)

    component.question = question

    db_session.add(form)
    await db_session.commit()

    return form


@pytest.fixture
def jsonlogic(request: FixtureRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return None


@pytest.fixture
async def form_with_classification(
    db_session: AsyncSession, form_title: str, jsonlogic: str | None, is_required: bool
) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    panel = FormIoPanelComponent(
        title="Panel 1",
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
        max_char_count=255,
        jsonlogic=jsonlogic,
        required=is_required,
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
    form.questions.append(question)
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
            max_char_count=255,
        )

        components = await primary_form.awaitable_attrs.components
        components.append(component)

        db_session.add(primary_form)
        await db_session.commit()

    return primary_form


@pytest.fixture
async def static_forms(db_session: AsyncSession) -> list[StaticForm]:
    static_forms = []
    for form_type in StaticFormTypeEnum:
        title = form_type.capitalize()
        form = StaticForm(
            type=StaticFormTypeEnum[form_type],
            title=f"{title}",
            display=FormIoFormDisplayEnum.form,
        )

        component = FormIoTextAreaComponent(
            label=f"{form_type}",
            description="",
            key=f"{form_type}",
            type=FormIoComponentTypeEnum.text_area,
            input=True,
            auto_expand=True,
            max_char_count=255,
        )

        components = await form.awaitable_attrs.components
        components.append(component)

        db_session.add(form)
        static_forms.append(form)

    await db_session.commit()

    return static_forms


@pytest.fixture
def attachment_filename(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)

    return "test.jpg"


@pytest.fixture
async def attachment(db_session: AsyncSession, melding: Melding, attachment_filename: str) -> Attachment:
    attachment = Attachment(original_filename=attachment_filename, melding=melding)
    attachment.file_path = f"/tmp/{uuid4()}/{attachment_filename}"

    db_session.add(attachment)
    await db_session.commit()

    return attachment


@pytest.fixture
async def melding_with_attachments(db_session: AsyncSession, melding: Melding) -> Melding:
    for i in range(9):
        filename = f"test{i}.jpg"
        attachment = Attachment(original_filename=filename, melding=melding)
        attachment.file_path = f"/tmp/{uuid4()}/{filename}"

        db_session.add(attachment)

    await db_session.commit()
    await db_session.refresh(melding)

    return melding


@pytest.fixture
async def geojson_geometry(request: FixtureRequest) -> dict[str, Any] | None:
    if hasattr(request, "param"):
        return dict(request.param)

    return None


@pytest.fixture
async def geojson(geojson_geometry: dict[str, Any]) -> dict[str, Any]:
    if geojson_geometry is not None:
        geometry = geojson_geometry
    else:
        geometry = {"type": "Point", "coordinates": [52.3680605, 4.897092]}

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {},
    }
