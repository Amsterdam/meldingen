from typing import Any, override

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import AssetType
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestCreateAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset-type:create"

    def get_method(self) -> str:
        return "POST"

    @pytest.mark.anyio
    async def test_asset_type_create(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name()), json={"name": "bla", "class_name": "bla.bla", "arguments": {}}
        )

        assert response.status_code == HTTP_201_CREATED

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "bla"
        assert body.get("class_name") == "bla.bla"
        assert body.get("arguments") == {}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None

    @pytest.mark.anyio
    async def test_asset_type_create_without_class_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={"name": "bla", "arguments": {}})

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
        response = await client.post(
            app.url_path_for(self.get_route_name()), json={"class_name": "bla.bla", "arguments": {}}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "name"]
        assert error.get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_asset_type_create_without_arguments(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name()), json={"name": "name", "class_name": "bla.bla"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "arguments"]
        assert error.get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_asset_type_create_without_name_and_class_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={"arguments": {}})

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

    @pytest.mark.anyio
    async def test_asset_type_create_without_name_class_name_and_arguments(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.get_route_name()), json={})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 3

        error = detail[0]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "name"]
        assert error.get("msg") == "Field required"

        error = detail[1]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "class_name"]
        assert error.get("msg") == "Field required"

        error = detail[2]
        assert error.get("type") == "missing"
        assert error.get("loc") == ["body", "arguments"]
        assert error.get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_asset_type_create_name_is_already_in_use(
        self, app: FastAPI, client: AsyncClient, auth_user: None, asset_type: AssetType
    ) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name()),
            json={"name": asset_type.name, "class_name": "bla.bla", "arguments": {}},
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestRetrieveAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset-type:retrieve"

    def get_method(self) -> str:
        return "GET"

    @override
    def get_path_params(self) -> dict[str, Any]:
        return {"asset_type_id": 123}

    @pytest.mark.anyio
    async def test_asset_type_retrieve_not_found(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name(), asset_type_id=123))

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_asset_type_retrieve(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "test_asset_type"
        assert body.get("class_name") == "test.AssetTypeClassName"
        assert body.get("arguments") == {}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None


class TestAssetTypeList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    def get_route_name(self) -> str:
        return "asset-type:list"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_list_all_asset_types(
        self, app: FastAPI, client: AsyncClient, auth_user: None, asset_types: list[AssetType]
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert len(data) == len(asset_types)

        assert response.headers.get("content-range") == "asset-type 0-49/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_asset_types_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected: int,
        asset_types: list[AssetType],
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected

        assert response.headers.get("content-range") == f"asset-type {offset}-{limit - 1 + offset}/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"name": "0", "class_name": "package.module.ClassName0", "arguments": {}},
                    {"name": "1", "class_name": "package.module.ClassName1", "arguments": {}},
                    {"name": "2", "class_name": "package.module.ClassName2", "arguments": {}},
                    {"name": "3", "class_name": "package.module.ClassName3", "arguments": {}},
                    {"name": "4", "class_name": "package.module.ClassName4", "arguments": {}},
                    {"name": "5", "class_name": "package.module.ClassName5", "arguments": {}},
                    {"name": "6", "class_name": "package.module.ClassName6", "arguments": {}},
                    {"name": "7", "class_name": "package.module.ClassName7", "arguments": {}},
                    {"name": "8", "class_name": "package.module.ClassName8", "arguments": {}},
                    {"name": "9", "class_name": "package.module.ClassName9", "arguments": {}},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"name": "9", "class_name": "package.module.ClassName9", "arguments": {}},
                    {"name": "8", "class_name": "package.module.ClassName8", "arguments": {}},
                    {"name": "7", "class_name": "package.module.ClassName7", "arguments": {}},
                    {"name": "6", "class_name": "package.module.ClassName6", "arguments": {}},
                    {"name": "5", "class_name": "package.module.ClassName5", "arguments": {}},
                    {"name": "4", "class_name": "package.module.ClassName4", "arguments": {}},
                    {"name": "3", "class_name": "package.module.ClassName3", "arguments": {}},
                    {"name": "2", "class_name": "package.module.ClassName2", "arguments": {}},
                    {"name": "1", "class_name": "package.module.ClassName1", "arguments": {}},
                    {"name": "0", "class_name": "package.module.ClassName0", "arguments": {}},
                ],
            ),
            (
                "name",
                SortingDirection.ASC,
                [
                    {"name": "0", "class_name": "package.module.ClassName0", "arguments": {}},
                    {"name": "1", "class_name": "package.module.ClassName1", "arguments": {}},
                    {"name": "2", "class_name": "package.module.ClassName2", "arguments": {}},
                    {"name": "3", "class_name": "package.module.ClassName3", "arguments": {}},
                    {"name": "4", "class_name": "package.module.ClassName4", "arguments": {}},
                    {"name": "5", "class_name": "package.module.ClassName5", "arguments": {}},
                    {"name": "6", "class_name": "package.module.ClassName6", "arguments": {}},
                    {"name": "7", "class_name": "package.module.ClassName7", "arguments": {}},
                    {"name": "8", "class_name": "package.module.ClassName8", "arguments": {}},
                    {"name": "9", "class_name": "package.module.ClassName9", "arguments": {}},
                ],
            ),
            (
                "name",
                SortingDirection.DESC,
                [
                    {"name": "9", "class_name": "package.module.ClassName9", "arguments": {}},
                    {"name": "8", "class_name": "package.module.ClassName8", "arguments": {}},
                    {"name": "7", "class_name": "package.module.ClassName7", "arguments": {}},
                    {"name": "6", "class_name": "package.module.ClassName6", "arguments": {}},
                    {"name": "5", "class_name": "package.module.ClassName5", "arguments": {}},
                    {"name": "4", "class_name": "package.module.ClassName4", "arguments": {}},
                    {"name": "3", "class_name": "package.module.ClassName3", "arguments": {}},
                    {"name": "2", "class_name": "package.module.ClassName2", "arguments": {}},
                    {"name": "1", "class_name": "package.module.ClassName1", "arguments": {}},
                    {"name": "0", "class_name": "package.module.ClassName0", "arguments": {}},
                ],
            ),
        ],
    )
    async def test_list_asset_types_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        asset_types: list[AssetType],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name()), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(0, len(data)):
            assert data[i]["name"] == expected[i]["name"]
            assert data[i]["class_name"] == expected[i]["class_name"]
            assert data[i]["arguments"] == expected[i]["arguments"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "asset-type 0-49/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "name",
                SortingDirection.DESC,
                [
                    {"name": "7", "class_name": "package.module.ClassName7", "arguments": {}},
                    {"name": "6", "class_name": "package.module.ClassName6", "arguments": {}},
                ],
            ),
            (
                3,
                1,
                "name",
                SortingDirection.ASC,
                [
                    {"name": "1", "class_name": "package.module.ClassName1", "arguments": {}},
                    {"name": "2", "class_name": "package.module.ClassName2", "arguments": {}},
                    {"name": "3", "class_name": "package.module.ClassName3", "arguments": {}},
                ],
            ),
        ],
    )
    async def test_list_asset_types_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        asset_types: list[AssetType],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name()),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(0, len(data)):
            assert data[i]["name"] == expected[i]["name"]
            assert data[i]["class_name"] == expected[i]["class_name"]
            assert data[i]["arguments"] == expected[i]["arguments"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"asset-type {offset}-{limit - 1 + offset}/10"


class TestUpdateAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset-type:update"

    def get_method(self) -> str:
        return "PATCH"

    @override
    def get_path_params(self) -> dict[str, Any]:
        return {"asset_type_id": 123}

    @pytest.mark.anyio
    async def test_update_asset_type_not_found(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=123), json={"name": "bla.bla"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_asset_type_name_already_in_use(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None, db_session: AsyncSession
    ) -> None:
        second_asset_type = AssetType("bla", "bla.bla", {})
        db_session.add(second_asset_type)
        await db_session.commit()

        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=second_asset_type.id), json={"name": asset_type.name}
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )

    @pytest.mark.anyio
    async def test_update_asset_type_name(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id), json={"name": "bla"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "bla"
        assert body.get("class_name") == "test.AssetTypeClassName"
        assert body.get("arguments") == {}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None

    @pytest.mark.anyio
    async def test_update_asset_type_class_name(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id), json={"class_name": "bla"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "test_asset_type"
        assert body.get("class_name") == "bla"
        assert body.get("arguments") == {}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None

    @pytest.mark.anyio
    async def test_update_asset_type_arguments(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id),
            json={"arguments": {"base_url": "http://localhost"}},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "test_asset_type"
        assert body.get("class_name") == "test.AssetTypeClassName"
        assert body.get("arguments") == {"base_url": "http://localhost"}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None

    @pytest.mark.anyio
    async def test_update_asset_type(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id),
            json={"name": "bla", "class_name": "bla.bla", "arguments": {"base_url": "http://localhost"}},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("name") == "bla"
        assert body.get("class_name") == "bla.bla"
        assert body.get("arguments") == {"base_url": "http://localhost"}
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None


class TestDeleteAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset-type:delete"

    def get_method(self) -> str:
        return "DELETE"

    @override
    def get_path_params(self) -> dict[str, Any]:
        return {"asset_type_id": 123}

    @pytest.mark.anyio
    async def test_delete_asset_type_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.delete(app.url_path_for(self.get_route_name(), asset_type_id=123))

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_delete_asset_type(
        self, app: FastAPI, client: AsyncClient, auth_user: None, asset_type: AssetType
    ) -> None:
        response = await client.delete(app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id))

        assert response.status_code == HTTP_204_NO_CONTENT
