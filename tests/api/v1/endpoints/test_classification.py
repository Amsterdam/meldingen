from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Classification
from tests.api.v1.endpoints.base import BaseCreate

ROUTE_NAME_LIST: Final[str] = "classification:list"
ROUTE_NAME_RETRIEVE: Final[str] = "classification:retrieve"
ROUTE_NAME_UPDATE: Final[str] = "classification:update"
ROUTE_NAME_DELETE: Final[str] = "classification:delete"


class TestClassificationCreate(BaseCreate):
    ROUTE_NAME_CREATE: Final[str] = "classification:create"

    @pytest.mark.asyncio
    async def test_create_classification(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"name": "bla"})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("name") == "bla"

    @pytest.mark.asyncio
    async def test_create_classification_name_min_length_violation(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"name": ""})

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
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"name": "bla"})

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestClassificationList:
    @pytest.mark.asyncio
    async def test_list_all_classifications(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classifications: list[Classification]
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_LIST))

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert len(data) == len(classifications)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_classifications(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected: int,
        classifications: list[Classification],
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_LIST), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected

    @pytest.mark.asyncio
    async def test_list_classifications_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
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
    async def test_list_classification_invalid_limit(
        self, app: FastAPI, client: AsyncClient, auth_user: None, limit: str | int, type: str, msg: str
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
    async def test_list_classification_invalid_offset(
        self, app: FastAPI, client: AsyncClient, auth_user: None, offset: str | int, type: str, msg: str
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


class TestClassificationRetrieve:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_retrieve_classification(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, classification_id=classification.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == 1
        assert data.get("name") == "bla"

    @pytest.mark.asyncio
    async def test_retrieve_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_retrieve_classification_unauthorized(
        self, app: FastAPI, client: AsyncClient, classification: Classification
    ) -> None:
        response = await client.get(app.url_path_for(ROUTE_NAME_RETRIEVE, classification_id=classification.id))

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"


class TestClassificationUpdate:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_update_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, classification_id=classification.id), json={"name": "bladiebla"}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("name") == "bladiebla"

    @pytest.mark.asyncio
    async def test_update_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, classification_id=404), json={"name": "bladiebla"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_update_classification_unauthorized(
        self, app: FastAPI, client: AsyncClient, classification: Classification
    ) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, classification_id=classification.id), json={"name": "bladiebla"}
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"

    @pytest.mark.asyncio
    async def test_update_classification_duplicate_name(
        self, app: FastAPI, client: AsyncClient, classifications: list[Classification], auth_user: None
    ) -> None:
        response = await client.patch(
            app.url_path_for(ROUTE_NAME_UPDATE, classification_id=1), json={"name": "category: 2"}
        )

        assert response.status_code == HTTP_409_CONFLICT

        data = response.json()
        assert (
            data.get("detail") == "The requested operation could not be completed due to a conflict with existing data."
        )


class TestClassificationDelete:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_delete_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification, auth_user: None
    ) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, classification_id=classification.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("classification_name,", ["bla"], indirect=True)
    async def test_delete_classification_unauthorized(
        self, app: FastAPI, client: AsyncClient, classification: Classification
    ) -> None:
        response = await client.delete(app.url_path_for(ROUTE_NAME_DELETE, classification_id=classification.id))

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"
