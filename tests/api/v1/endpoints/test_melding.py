from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

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

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("id") == 1
    assert data.get("text") == "This is a test melding."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, offset, expected_result",
    [(10, 0, 1), (5, 0, 1), (10, 10, 0), (1, 1, 0)],
)
async def test_list_meldingen(
    app: FastAPI,
    client: AsyncClient,
    limit: int,
    offset: int,
    expected_result: int,
) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit, "offset": offset})

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == expected_result


@pytest.mark.asyncio
async def test_retrieve_melding(app: FastAPI, client: AsyncClient) -> None:
    response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, melding_id=1))

    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data.get("id") == 1
    assert data.get("text") == "This is a test melding."
