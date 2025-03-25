from typing import Any, Final

from fastapi import FastAPI
from httpx import AsyncClient, Response
from pytest import fixture
from pytest_bdd import parsers, then, when
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from meldingen.models import Classification
from tests.scenarios.conftest import async_step

ROUTE_NAME_CREATE: Final[str] = "melding:create"


@fixture
def api_response() -> Response:
    return Response(0)


@fixture
def my_melding() -> dict[str, Any]:
    return {}


@when(parsers.parse('I create a melding with text "{text:l}"'), target_fixture="my_melding")
@async_step
async def create_melding_with_text(text: str, app: FastAPI, client: AsyncClient) -> dict[str, Any]:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"text": text})
    assert response.status_code == HTTP_201_CREATED

    body = response.json()
    assert isinstance(body, dict)

    return body


@then(parsers.parse('the melding should be classified as "{classification_name:l}"'))
def the_melding_should_be_classified_as(
    classification: Classification, my_melding: dict[str, Any], classification_name: str
) -> None:
    assert classification.name == classification_name
    assert my_melding.get("classification") == classification.id


@then("the melding should contain a token", target_fixture="token")
def the_melding_should_contain_a_token(my_melding: dict[str, Any]) -> str:
    assert isinstance(my_melding["token"], str)
    return my_melding["token"]


@then("I should receive a response with the current content of my melding", target_fixture="my_melding")
def i_should_receive_an_updated_melding(
    api_response: Response,
    my_melding: dict[str, Any],
) -> dict[str, Any]:
    assert api_response.status_code == HTTP_200_OK
    body = api_response.json()
    assert isinstance(body, dict)

    assert body.get("id") == my_melding["id"]

    return body
