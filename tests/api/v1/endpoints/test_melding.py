from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Melding

ROUTE_NAME_CREATE: Final[str] = "melding:create"
ROUTE_NAME_LIST: Final[str] = "melding:list"
ROUTE_NAME_RETRIEVE: Final[str] = "melding:retrieve"


class TestMeldingRoutes:
    @pytest.mark.asyncio
    async def test_routes_exist(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={})
        assert res.status_code != HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_invalid_input_raises_error(self, app: FastAPI, client: AsyncClient) -> None:
        res = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={})
        assert res.status_code == HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_melding(app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

    assert response.status_code == HTTP_201_CREATED

    data = response.json()
    assert data.get("id") == 1
    assert data.get("text") == "This is a test melding."


@pytest.mark.asyncio
async def test_create_melding_text_minimum_length_violation(app: FastAPI, client: AsyncClient) -> None:
    response = await client.post(app.url_path_for(ROUTE_NAME_CREATE), json={"text": ""})

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    detail = data.get("detail")
    assert len(detail) == 1

    violation = detail[0]
    assert violation.get("type") == "string_too_short"
    assert violation.get("loc") == ["body", "text"]
    assert violation.get("msg") == "String should have at least 1 character"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, offset, expected_result",
    [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
)
async def test_list_meldingen(
    app: FastAPI,
    client: AsyncClient,
    auth_user: None,
    limit: int,
    offset: int,
    expected_result: int,
    test_meldingen: list[Melding],
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit, "offset": offset})

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == expected_result


@pytest.mark.asyncio
async def test_list_meldingen_unauthorized(app: FastAPI, client: AsyncClient) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, type, msg",
    [
        ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
        (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
    ],
)
async def test_list_melding_invalid_limit(
    app: FastAPI, client: AsyncClient, auth_user: None, limit: str | int, type: str, msg: str
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit})

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    body = response.json()
    detail = body.get("detail")
    assert len(detail) == 1

    violation = detail[0]
    assert violation.get("type") == type
    assert violation.get("loc") == ["query", "limit"]
    assert violation.get("msg") == msg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "offset, type, msg",
    [
        ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
        (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
    ],
)
async def test_list_melding_invalid_offset(
    app: FastAPI, client: AsyncClient, auth_user: None, offset: str | int, type: str, msg: str
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"offset": offset})

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    body = response.json()
    detail = body.get("detail")
    assert len(detail) == 1

    violation = detail[0]
    assert violation.get("type") == type
    assert violation.get("loc") == ["query", "offset"]
    assert violation.get("msg") == msg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "melding_text", ["Er ligt poep op de stoep.", "Er is een matras naast de prullenbak gedumpt."], indirect=True
)
async def test_retrieve_melding(app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, melding_id=test_melding.id))

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("id") == test_melding.id
    assert data.get("text") == test_melding.text


@pytest.mark.asyncio
async def test_retrieve_melding_that_does_not_exist(app: FastAPI, client: AsyncClient, auth_user: None) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, melding_id=1))

    assert response.status_code == HTTP_404_NOT_FOUND

    body = response.json()
    assert body.get("detail") == "Not Found"


@pytest.mark.asyncio
async def test_retrieve_melding_unauthorized(app: FastAPI, client: AsyncClient, test_melding: Melding) -> None:
    """Tests that a 401 response is given when no access token is provided through the Authorization header."""
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, melding_id=test_melding.id))

    assert response.status_code == HTTP_401_UNAUTHORIZED

    data = response.json()
    assert data.get("detail") == "Not authenticated"
