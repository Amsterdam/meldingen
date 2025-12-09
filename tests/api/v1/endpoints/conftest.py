from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from meldingen_core.statemachine import MeldingBackofficeStates, MeldingStates
from pydantic import TypeAdapter
from pytest import FixtureRequest
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from meldingen.authentication import authenticate_user
from meldingen.models import (
    AnswerTypeEnum,
    Asset,
    AssetType,
    Attachment,
    Classification,
    Form,
    FormIoComponentTypeEnum,
    FormIoDateComponent,
    FormIoFormDisplayEnum,
    FormIoPanelComponent,
    FormIoTextAreaComponent,
    FormIoTimeComponent,
    Melding,
    Question,
    StaticForm,
    StaticFormTypeEnum,
    TextAnswer,
    TimeAnswer,
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
def melding_public_id(request: FixtureRequest) -> str:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return "PUBMEL"


@pytest.fixture
def melding_street(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
def melding_house_number(request: FixtureRequest) -> int | None:
    if hasattr(request, "param") and request.param is not None:
        return int(request.param)
    else:
        return None


@pytest.fixture
def melding_house_number_addition(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
def melding_postal_code(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
def melding_city(request: FixtureRequest) -> str | None:
    if hasattr(request, "param") and request.param is not None:
        return str(request.param)
    else:
        return None


@pytest.fixture
async def melding(
    db_session: AsyncSession,
    melding_text: str,
    melding_public_id: str,
    melding_state: str | None,
    melding_token: str | None,
    melding_token_expires: datetime | None,
    melding_geo_location: str | None,
    melding_street: str | None,
    melding_house_number: int | None,
    melding_house_number_addition: str | None,
    melding_postal_code: str | None,
    melding_city: str | None,
    melding_email: str | None,
    melding_phone: str | None,
) -> Melding:
    melding = Melding(text=melding_text)
    melding.public_id = melding_public_id

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
    melding.street = melding_street
    melding.postal_code = melding_postal_code
    melding.house_number = melding_house_number
    melding.house_number_addition = melding_house_number_addition
    melding.city = melding_city

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
async def melding_with_classification_with_asset_type(
    db_session: AsyncSession,
    melding: Melding,
    classification_with_asset_type: Classification,
) -> Melding:
    asset_type: AssetType = await classification_with_asset_type.awaitable_attrs.asset_type
    assert asset_type is not None
    asset = Asset(external_id="test_external_id", type=asset_type, melding=melding)

    melding.assets.append(asset)
    melding.classification = classification_with_asset_type

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
async def melding_with_text_answers(
    db_session: AsyncSession, melding_with_classification: Melding, form_with_multiple_questions: Form
) -> Melding:
    questions = await form_with_multiple_questions.awaitable_attrs.questions

    numbers = [6, 3, 2, 9, 7, 1, 8, 4, 5, 0]
    for i in numbers:
        db_session.add(
            TextAnswer(
                text=f"Answer {i}",
                melding=melding_with_classification,
                question=questions[i],
                type=AnswerTypeEnum.text,
            )
        )

    await db_session.commit()

    return melding_with_classification


@pytest.fixture
async def melding_with_time_answers(
    db_session: AsyncSession, melding_with_classification: Melding, form_with_multiple_questions: Form
) -> Melding:
    questions = await form_with_multiple_questions.awaitable_attrs.questions

    for i in [1, 2, 5, 6]:
        db_session.add(
            TimeAnswer(
                time=f"10:0{i}",
                melding=melding_with_classification,
                question=questions[i],
                type=AnswerTypeEnum.time,
            )
        )

    await db_session.commit()

    return melding_with_classification


@pytest.fixture
async def melding_with_different_answer_types(
     db_session: AsyncSession, melding_with_classification: Melding, formio_time_component: FormIoTimeComponent, formio_text_area_component: FormIoTextAreaComponent
) -> Melding:
    classification = melding_with_classification.classification
    form = Form(title="test_form", display=FormIoFormDisplayEnum.form, classification=classification)

    panel1 = FormIoPanelComponent(
        title="Panel 1",
        label="Page 1",
        key="page1",
        input=False,
        type=FormIoComponentTypeEnum.panel,
        position=1,
    )

    form.components.append(panel1)

    db_session.add(form)
    await db_session.commit()

    formio_text_area_component.parent = panel1

    panel2 = FormIoPanelComponent(
        title="Panel 2",
        label="Page 2",
        key="page2",
        input=False,
        type=FormIoComponentTypeEnum.panel,
        position=2,
    )

    form_components = await form.awaitable_attrs.components
    form_components.append(panel2)

    formio_time_component.parent = panel2

    text_answer = TextAnswer(
        text="John Doe",
        melding=melding_with_classification,
        question=Question(text="What is your name?", form=form, component=formio_text_area_component),
        type=AnswerTypeEnum.text,
    )

    db_session.add(text_answer)
    await db_session.commit()

    time_answer = TimeAnswer(
        time="14:30",
        melding=melding_with_classification,
        question=Question(text="What time is it?", form=form, component=formio_time_component),
        type=AnswerTypeEnum.time,
    )

    db_session.add(time_answer)
    await db_session.commit()

    return melding_with_classification


@pytest.fixture
async def melding_with_asset(
    db_session: AsyncSession, melding_with_classification_with_asset_type: Melding, asset: Asset
) -> Melding:
    melding_with_classification_with_asset_type.assets.append(asset)

    await db_session.commit()

    return melding_with_classification_with_asset_type


@pytest.fixture
async def melding_with_assets(
    db_session: AsyncSession,
    melding_with_classification_with_asset_type: Melding,
    asset_type: AssetType,
) -> Melding:
    for i in range(5):
        asset = Asset(
            external_id=f"external_id_{i}", type=asset_type, melding=melding_with_classification_with_asset_type
        )
        db_session.add(asset)
        melding_with_classification_with_asset_type.assets.append(asset)
        db_session.add(melding_with_classification_with_asset_type)

    await db_session.commit()

    return melding_with_classification_with_asset_type


@pytest.fixture
async def melding_with_assets_with_classification_and_asset_type(
    db_session: AsyncSession,
    melding: Melding,
    classification_with_asset_type: Classification,
) -> Melding:
    asset_type: AssetType = await classification_with_asset_type.awaitable_attrs.asset_type
    assert asset_type is not None

    melding.classification = classification_with_asset_type

    for i in range(5):
        asset = Asset(external_id=f"external_id_{i}", type=asset_type, melding=melding)
        db_session.add(asset)
        melding.assets.append(asset)
        db_session.add(melding)

    await db_session.commit()

    return melding


@pytest.fixture
async def melding_with_some_answers(
    db_session: AsyncSession, melding_with_classification: Melding, form_with_multiple_questions: Form
) -> Melding:
    questions = await form_with_multiple_questions.awaitable_attrs.questions

    numbers = [6, 3, 2, 9, 7]
    for i in numbers:
        db_session.add(
            TextAnswer(
                text=f"Answer {i}",
                melding=melding_with_classification,
                question=questions[i],
                type=AnswerTypeEnum.text,
            )
        )

    await db_session.commit()

    return melding_with_classification


@pytest.fixture
async def meldingen(db_session: AsyncSession, melding_text: str) -> list[Melding]:
    meldingen = []
    for i in range(10):
        melding = Melding(text=f"{melding_text} {i}")
        melding.public_id = f"MELDI{i}"
        melding.state = MeldingBackofficeStates.PROCESSING

        db_session.add(melding)
        meldingen.append(melding)

    await db_session.commit()

    return meldingen


@pytest.fixture
def melding_locations(request: FixtureRequest) -> list[str]:
    if hasattr(request, "param"):
        return request.param

    return []


@pytest.fixture
async def meldingen_with_location(db_session: AsyncSession, melding_locations: list[str]) -> list[Melding]:
    meldingen = []
    i = 0
    for location in melding_locations:
        i += 1
        melding = Melding(text=f"Melding {i}")
        melding.public_id = f"MELDI{i}"
        melding.geo_location = location
        melding.state = MeldingBackofficeStates.PROCESSING

        db_session.add(melding)
        meldingen.append(melding)

    await db_session.commit()

    for melding in meldingen:
        await db_session.refresh(melding)

    return meldingen


@pytest.fixture
def melding_states(request: FixtureRequest) -> list[MeldingStates]:
    if hasattr(request, "param"):
        param: list[MeldingStates] = request.param
        return param

    return []


@pytest.fixture
async def meldingen_with_different_states(
    db_session: AsyncSession, melding_states: list[MeldingStates]
) -> list[Melding]:
    meldingen = []
    i = 0
    for state in melding_states:
        i += 1
        melding = Melding(text=f"Melding {i}")
        melding.public_id = f"MELDI{i}"
        melding.state = state

        db_session.add(melding)
        meldingen.append(melding)

    await db_session.commit()

    for melding in meldingen:
        await db_session.refresh(melding)

    return meldingen


@pytest.fixture
async def meldingen_with_different_states_and_locations(
    db_session: AsyncSession, melding_states: list[MeldingStates], melding_locations: list[str]
) -> list[Melding]:
    meldingen = []
    i = 0
    for state in melding_states:
        location = melding_locations[i]
        i += 1
        melding = Melding(text=f"Melding {i}")
        melding.public_id = f"MELDI{i}"
        melding.state = state
        melding.geo_location = location

        db_session.add(melding)
        meldingen.append(melding)

    await db_session.commit()

    for melding in meldingen:
        await db_session.refresh(melding)

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
async def classification_with_asset_type(db_session: AsyncSession, asset_type: AssetType) -> Classification:
    classification = Classification("test_classification")
    classification.asset_type = asset_type

    db_session.add(classification)
    await db_session.commit()

    return classification


@pytest.fixture
async def classification_with_asset_type_and_form(db_session: AsyncSession) -> Classification:
    classification = Classification("test_classification")
    classification.asset_type = AssetType(name="test_asset_type", class_name="test_class", arguments={}, max_assets=3)
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
def jsonlogic(request: FixtureRequest) -> str | None:
    if hasattr(request, "param"):
        return str(request.param)
    else:
        return None


@pytest.fixture
def formio_text_area_component(
    db_session: AsyncSession,
    conditional: dict[str, Any],
    is_required: bool,
    jsonlogic: str | None,
) -> FormIoTextAreaComponent:

    component = FormIoTextAreaComponent(
        label="Wat is uw klacht?",
        description="",
        key="wat-is-uw_klacht",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        max_char_count=255,
        conditional=conditional,
        required=is_required,
        jsonlogic=jsonlogic,
    )
    db_session.add(component)

    return component


@pytest.fixture
def conditional(request: FixtureRequest) -> dict[str, Any] | None:
    if hasattr(request, "param"):
        return dict(request.param)
    else:
        return {"show": True, "when": "A", "eq": "B"}


@pytest.fixture
async def form(
    db_session: AsyncSession,
    form_title: str,
    formio_text_area_component: FormIoTextAreaComponent,
) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    components = await form.awaitable_attrs.components
    components.append(formio_text_area_component)

    question = Question(text=formio_text_area_component.description, form=form)

    formio_text_area_component.question = question

    db_session.add(form)
    await db_session.commit()

    return form


@pytest.fixture
def form_panel(db_session: AsyncSession) -> FormIoPanelComponent:
    panel = FormIoPanelComponent(
        title="Panel 1",
        label="Page 1",
        key="page1",
        input=False,
        type=FormIoComponentTypeEnum.panel,
    )
    db_session.add(panel)
    return panel


@pytest.fixture
def formio_date_component_day_range(request: FixtureRequest) -> int:
    if hasattr(request, "param"):
        return int(request.param)
    else:
        return 7


@pytest.fixture
def formio_date_component(db_session: AsyncSession, formio_date_component_day_range: int) -> FormIoDateComponent:
    component = FormIoDateComponent(
        label="Datum",
        description="",
        key="datum",
        type=FormIoComponentTypeEnum.date,
        input=True,
        day_range=formio_date_component_day_range,
    )
    db_session.add(component)
    return component


@pytest.fixture
async def form_with_date_component(
    db_session: AsyncSession,
    form_title: str,
    form_panel: FormIoPanelComponent,
    formio_date_component: FormIoDateComponent,
    conditional: dict[str, Any],
) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    formio_date_component.conditional = conditional

    form_components = await form.awaitable_attrs.components
    form_components.append(form_panel)

    panel_components = await form_panel.awaitable_attrs.components
    panel_components.append(formio_date_component)

    question = Question(text="Vanaf welke dag speelt dit?", form=form)

    formio_date_component.question = question

    db_session.add(form)
    await db_session.commit()

    return form


@pytest.fixture
def formio_time_component(db_session: AsyncSession, is_required: bool) -> FormIoTimeComponent:
    component = FormIoTimeComponent(
        label="Tijd",
        description="",
        key="tijd",
        type=FormIoComponentTypeEnum.time,
        input=True,
        required=is_required,
    )
    db_session.add(component)
    return component


@pytest.fixture
async def form_with_time_component(
    db_session: AsyncSession,
    form_title: str,
    form_panel: FormIoPanelComponent,
    formio_time_component: FormIoTimeComponent,
    melding_with_classification: Melding,
    conditional: dict[str, Any],
) -> Form:
    form = Form(
        title=form_title, display=FormIoFormDisplayEnum.form, classification=melding_with_classification.classification
    )

    formio_time_component.conditional = conditional

    form_components = await form.awaitable_attrs.components
    form_components.append(form_panel)

    panel_components = await form_panel.awaitable_attrs.components
    panel_components.append(formio_time_component)

    question = Question(text="Hoe laat was dit?", form=form)

    formio_time_component.question = question

    db_session.add(form)
    await db_session.commit()

    return form


@pytest.fixture
async def form_with_classification(
    db_session: AsyncSession,
    form_title: str,
    formio_text_area_component: FormIoTextAreaComponent,
    conditional: dict[str, Any],
) -> Form:
    form = Form(title=form_title, display=FormIoFormDisplayEnum.form)

    panel = FormIoPanelComponent(
        title="Panel 1",
        label="Page 1",
        key="page1",
        input=False,
        type=FormIoComponentTypeEnum.panel,
        conditional=conditional,
    )

    panel_components = await panel.awaitable_attrs.components
    panel_components.append(formio_text_area_component)

    components = await form.awaitable_attrs.components
    components.append(panel)

    question = Question(text=formio_text_area_component.description, form=form)

    db_session.add(question)

    formio_text_area_component.question = question

    classification_name = "test_classification"

    result = await db_session.execute(select(Classification).where(Classification.name == classification_name))
    classification = result.scalars().one_or_none()
    if classification is None:
        classification = Classification(classification_name)
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
            jsonlogic='{"if": [{"<=": [{"length": [{"var": "text"}]},1000]},true,"Meldingtekst moet 1000 tekens of minder zijn."]}',
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
    attachment = Attachment(original_filename=attachment_filename, original_media_type="image/jpeg", melding=melding)
    attachment.file_path = f"/tmp/{uuid4()}/{attachment_filename}"

    db_session.add(attachment)
    await db_session.commit()

    return attachment


@pytest.fixture
async def melding_with_attachments(db_session: AsyncSession, melding: Melding) -> Melding:
    for i in range(9):
        filename = f"test{i}.jpg"
        attachment = Attachment(original_filename=filename, original_media_type="image/jpeg", melding=melding)
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


@pytest.fixture
def asset_type_name(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)

    return "test_asset_type"


@pytest.fixture
def asset_type_class_name(request: FixtureRequest) -> str:
    if hasattr(request, "param"):
        return str(request.param)

    return "test.AssetTypeClassName"


@pytest.fixture
def asset_type_arguments(request: FixtureRequest) -> dict[str, Any]:
    return {}


@pytest.fixture
def asset_type_max_assets(request: FixtureRequest) -> int:
    return 10


@pytest.fixture
async def asset_type(
    db_session: AsyncSession,
    asset_type_name: str,
    asset_type_class_name: str,
    asset_type_arguments: dict[str, Any],
    asset_type_max_assets: int,
) -> AssetType:
    asset_type = AssetType(
        name=asset_type_name,
        class_name=asset_type_class_name,
        arguments=asset_type_arguments,
        max_assets=asset_type_max_assets,
    )

    db_session.add(asset_type)
    await db_session.commit()

    return asset_type


@pytest.fixture
async def asset_types(db_session: AsyncSession) -> list[AssetType]:
    asset_types = []
    for i in range(10):
        asset_type = AssetType(f"{i}", f"package.module.ClassName{i}", {}, 3)
        db_session.add(asset_type)
        asset_types.append(asset_type)

    await db_session.commit()

    return asset_types


@pytest.fixture
async def asset(db_session: AsyncSession, asset_type: AssetType, melding: Melding) -> Asset:
    asset = Asset("some_external_id", asset_type, melding=melding)

    db_session.add(asset)
    await db_session.commit()

    return asset
