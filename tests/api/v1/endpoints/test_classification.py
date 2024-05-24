from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Classification, FormIoForm
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestClassificationCreate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "classification:create"
    METHOD: Final[str] = "POST"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    async def test_create_classification(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME), json={"name": "bla"})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("name") == "bla"
        assert data.get("form", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.asyncio
    async def test_create_classification_name_min_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME), json={"name": ""})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "string_too_short"
        assert violation.get("loc") == ["body", "name"]
        assert violation.get("msg") == "String should have at least 1 character"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_create_classification_duplicate_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME), json={"name": "bla"})

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestClassificationList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "classification:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    async def test_list_all_classifications(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classifications: list[Classification]
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert len(data) == len(classifications)

        assert response.headers.get("content-range") == "classification 0-49/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_classifications_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected: int,
        classifications: list[Classification],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected

        assert response.headers.get("content-range") == f"classification {offset}-{limit - 1 + offset}/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"name": "category: 0", "id": 1, "form": None},
                    {"name": "category: 1", "id": 2, "form": None},
                    {"name": "category: 2", "id": 3, "form": None},
                    {"name": "category: 3", "id": 4, "form": None},
                    {"name": "category: 4", "id": 5, "form": None},
                    {"name": "category: 5", "id": 6, "form": None},
                    {"name": "category: 6", "id": 7, "form": None},
                    {"name": "category: 7", "id": 8, "form": None},
                    {"name": "category: 8", "id": 9, "form": None},
                    {"name": "category: 9", "id": 10, "form": None},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"name": "category: 9", "id": 10, "form": None},
                    {"name": "category: 8", "id": 9, "form": None},
                    {"name": "category: 7", "id": 8, "form": None},
                    {"name": "category: 6", "id": 7, "form": None},
                    {"name": "category: 5", "id": 6, "form": None},
                    {"name": "category: 4", "id": 5, "form": None},
                    {"name": "category: 3", "id": 4, "form": None},
                    {"name": "category: 2", "id": 3, "form": None},
                    {"name": "category: 1", "id": 2, "form": None},
                    {"name": "category: 0", "id": 1, "form": None},
                ],
            ),
            (
                "name",
                SortingDirection.ASC,
                [
                    {"name": "category: 0", "id": 1, "form": None},
                    {"name": "category: 1", "id": 2, "form": None},
                    {"name": "category: 2", "id": 3, "form": None},
                    {"name": "category: 3", "id": 4, "form": None},
                    {"name": "category: 4", "id": 5, "form": None},
                    {"name": "category: 5", "id": 6, "form": None},
                    {"name": "category: 6", "id": 7, "form": None},
                    {"name": "category: 7", "id": 8, "form": None},
                    {"name": "category: 8", "id": 9, "form": None},
                    {"name": "category: 9", "id": 10, "form": None},
                ],
            ),
            (
                "name",
                SortingDirection.DESC,
                [
                    {"name": "category: 9", "id": 10, "form": None},
                    {"name": "category: 8", "id": 9, "form": None},
                    {"name": "category: 7", "id": 8, "form": None},
                    {"name": "category: 6", "id": 7, "form": None},
                    {"name": "category: 5", "id": 6, "form": None},
                    {"name": "category: 4", "id": 5, "form": None},
                    {"name": "category: 3", "id": 4, "form": None},
                    {"name": "category: 2", "id": 3, "form": None},
                    {"name": "category: 1", "id": 2, "form": None},
                    {"name": "category: 0", "id": 1, "form": None},
                ],
            ),
        ],
    )
    async def test_list_classifications_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        classifications: list[Classification],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(0, len(data)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["name"] == expected[i]["name"]
            assert data[i]["form"] == expected[i]["form"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "classification 0-49/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "name",
                SortingDirection.DESC,
                [{"name": "category: 7", "id": 8, "form": None}, {"name": "category: 6", "id": 7, "form": None}],
            ),
            (
                3,
                1,
                "name",
                SortingDirection.ASC,
                [
                    {"name": "category: 1", "id": 2, "form": None},
                    {"name": "category: 2", "id": 3, "form": None},
                    {"name": "category: 3", "id": 4, "form": None},
                ],
            ),
        ],
    )
    async def test_list_classifications_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        classifications: list[Classification],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(0, len(data)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["name"] == expected[i]["name"]
            assert data[i]["form"] == expected[i]["form"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"classification {offset}-{limit - 1 + offset}/10"

    @pytest.mark.asyncio
    async def test_list_classification_with_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form_with_classification: FormIoForm
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert len(body) == 1
        assert body[0].get("form") == form_with_classification.id

    @pytest.mark.asyncio
    async def test_list_classifications_sort_on_relationship(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form_with_classification: FormIoForm
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"sort": '["form", "ASC"]'})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "attribute_not_found"
        assert violation.get("loc") == ["query", "sort"]
        assert violation.get("msg") == "Cannot sort on relationship form"


class TestClassificationRetrieve(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "classification:retrieve"
    METHOD: Final[str] = "GET"
    PATH_PARAMS: dict[str, Any] = {"classification_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_retrieve_classification(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=classification.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == 1
        assert data.get("name") == "bla"
        assert data.get("form", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.asyncio
    async def test_retrieve_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_retrieve_classification_with_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification_with_form: Classification
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=classification_with_form.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("form") == classification_with_form.id


class TestClassificationUpdate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "classification:update"
    METHOD: Final[str] = "PATCH"
    PATH_PARAMS: dict[str, Any] = {"classification_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_update_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, classification_id=classification.id), json={"name": "bladiebla"}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("name") == "bladiebla"
        assert data.get("form", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.asyncio
    async def test_update_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, classification_id=404), json={"name": "bladiebla"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_update_classification_duplicate_name(
        self, app: FastAPI, client: AsyncClient, classifications: list[Classification], auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, classification_id=1), json={"name": "category: 2"}
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )

    @pytest.mark.asyncio
    async def test_update_classification_with_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification_with_form: Classification
    ) -> None:
        response = await client.patch(app.url_path_for(self.ROUTE_NAME, classification_id=1), json={"name": "new_name"})

        assert response.status_code == HTTP_200_OK

        form = await classification_with_form.awaitable_attrs.form

        body = response.json()
        assert body.get("name") == "new_name"
        assert body.get("form") == form.id


class TestClassificationDelete(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "classification:delete"
    METHOD: Final[str] = "DELETE"
    PATH_PARAMS: dict[str, Any] = {"classification_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_delete_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
    ) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, classification_id=classification.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_id", [0, -1])
    async def test_delete_invalid_id(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification_id: int
    ) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, classification_id=classification_id))

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than_equal"
        assert violation.get("loc") == ["path", "classification_id"]
        assert violation.get("msg") == "Input should be greater than or equal to 1"
