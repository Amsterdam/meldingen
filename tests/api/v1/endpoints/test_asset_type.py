import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_201_CREATED, HTTP_422_UNPROCESSABLE_ENTITY

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestCreateAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset-type:create"

    def get_method(self) -> str:
        return "POST"

    @pytest.mark.anyio
    async def test_asset_type_create(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name()), json={"name": "bla", "class_name": "bla.bla"}
        )

        assert response.status_code == HTTP_201_CREATED

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "bla"
        assert body.get("class_name") == "bla.bla"
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None

    @pytest.mark.anyio
    async def test_asset_type_create_without_class_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={"name": "bla"})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "class_name"]
        assert error.get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_asset_type_create_without_name(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={"class_name": "bla.bla"})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "name"]
        assert error.get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_asset_type_create_without_name_and_class_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 2

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "name"]
        assert error.get("msg") == "Field required"

        error = detail[1]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "class_name"]
        assert error.get("msg") == "Field required"
