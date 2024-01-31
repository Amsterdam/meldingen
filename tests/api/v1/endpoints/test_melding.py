from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_200_OK

ROUTE_NAME_CREATE: Final[str] = "melding:create"

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
