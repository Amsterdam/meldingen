from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient
from pytest_bdd import given, parsers, when
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from meldingen.models import (
    AnswerTypeEnum,
    Classification,
    Form,
    FormIoComponentTypeEnum,
    FormIoFormDisplayEnum,
    FormIoPanelComponent,
    FormIoTextAreaComponent,
    Question,
)
from tests.scenarios.conftest import async_step

ROUTE_RETRIEVE_ADDITIONAL_QUESTIONS: Final[str] = "form:classification"
ROUTE_ANSWER_QUESTION: Final[str] = "melding:answer-question"


@given("there is a form for additional questions", target_fixture="form")
@async_step
async def there_is_a_form_for_this_classification(db_session: AsyncSession, classification: Classification) -> Form:
    form = Form(
        title="Extra questions",
        display=FormIoFormDisplayEnum.wizard,
        classification=classification,
    )

    db_session.add(form)
    await db_session.commit()

    return form


@given("the form contains a panel", target_fixture="form_panel")
@async_step
async def the_additional_form_contains_a_panel(db_session: AsyncSession, form: Form) -> FormIoPanelComponent:

    panel = FormIoPanelComponent(
        title="Describe the situation more clearly",
        label="panel-1",
        key="panel",
        input=False,
        type=FormIoComponentTypeEnum.panel,
        form=form,
    )

    db_session.add(panel)
    await db_session.commit()
    return panel


@given(
    parsers.parse('the panel contains a text area component with the question "{question_text:l}"'),
    target_fixture="form_text_area_component",
)
@async_step
async def the_additional_form_contains_a_text_area_component(
    db_session: AsyncSession,
    form: Form,
    form_panel: FormIoPanelComponent,
    question_text: str,
) -> FormIoTextAreaComponent:

    question = Question(text=question_text, form=form)

    db_session.add(question)

    text_area_component = FormIoTextAreaComponent(
        label="Why is this important?",
        key="why-is-this-important",
        type=FormIoComponentTypeEnum.text_area,
        input=True,
        auto_expand=True,
        max_char_count=255,
        description="Ask why",
        parent=form_panel,
        required=True,
    )

    text_area_component.question = question

    db_session.add(text_area_component)
    form.questions.append(question)
    await db_session.commit()

    return text_area_component


@when("I retrieve the additional questions through my classification", target_fixture="additional_questions")
@async_step
async def retrieve_additional_questions_through_classification(
    client: AsyncClient,
    app: FastAPI,
    my_melding: dict[str, Any],
) -> dict[str, Any]:
    classification = my_melding.get("classification")
    assert isinstance(classification, dict)

    response = await client.get(
        app.url_path_for(ROUTE_RETRIEVE_ADDITIONAL_QUESTIONS, classification_id=classification.get("id"))
    )
    assert response.status_code == HTTP_200_OK

    body = response.json()
    assert isinstance(body, dict)

    return body


@when(parsers.parse('I answer the additional questions with the text "{text:l}"'))
@async_step
async def answer_additional_questions(
    client: AsyncClient,
    app: FastAPI,
    my_melding: dict[str, Any],
    token: str,
    additional_questions: dict[str, Any],
    text: str,
) -> None:
    question_id = additional_questions["components"][0]["components"][0]["question"]

    response = await client.post(
        app.url_path_for(ROUTE_ANSWER_QUESTION, melding_id=my_melding["id"], question_id=question_id),
        params={"token": token},
        json={"text": text, "type": AnswerTypeEnum.text},
    )

    assert response.status_code == HTTP_201_CREATED
