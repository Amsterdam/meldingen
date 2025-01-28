from typing import Final, Any

from fastapi import FastAPI
from httpx import AsyncClient
from pytest_bdd import when, parsers, then

from tests.scenarios.conftest import async_to_sync

ROUTE_NAME_CREATE: Final[str] = "melding:create"


@when(parsers.parse('I create a melding with text "{text:l}"'), target_fixture="create_melding_response_body")
@async_to_sync
async def create_melding_with_text(text: str, app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"text": text})
    assert response.status_code == 201

    return response.json()


@then(parsers.parse('the melding should be classified as "{classification:l}"'))
def the_melding_should_be_classified_as(create_melding_response_body: dict[str, Any], classification: str) -> None:
    assert create_melding_response_body.get("classification") == classification
