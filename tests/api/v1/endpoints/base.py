from abc import ABCMeta, abstractmethod
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_422_UNPROCESSABLE_ENTITY


class BaseUnauthorizedTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @abstractmethod
    def get_method(self) -> str: ...

    def get_path_params(self) -> dict[str, Any]:
        return {}

    @pytest.mark.anyio
    async def test_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"


class BasePaginationParamsTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, type, msg",
        [
            ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
            (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
        ],
    )
    async def test_list_invalid_limit(
        self, app: FastAPI, client: AsyncClient, auth_user: None, limit: str | int, type: str, msg: str
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"limit": limit})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 2

        violation = detail[0]
        assert violation.get("type") == type
        assert violation.get("loc") == ["query", "limit"]
        assert violation.get("msg") == msg

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "offset, type, msg",
        [
            ("abc", "int_parsing", "Input should be a valid integer, unable to parse string as an integer"),
            (-1, "greater_than_equal", "Input should be greater than or equal to 0"),
        ],
    )
    async def test_list_invalid_offset(
        self, app: FastAPI, client: AsyncClient, auth_user: None, offset: str | int, type: str, msg: str
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"offset": offset})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 2

        violation = detail[0]
        assert violation.get("type") == type
        assert violation.get("loc") == ["query", "offset"]
        assert violation.get("msg") == msg


class BaseSortParamsTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @pytest.mark.anyio
    async def test_list_sort_invalid_json(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"sort": '["id", "ASC", "bla"'})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "json_invalid"
        assert violation.get("loc") == ["query", "sort"]
        assert violation.get("msg") == "Invalid JSON: EOF while parsing a list at line 1 column 19"

    @pytest.mark.anyio
    async def test_list_sort_invalid_json_array(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"sort": '["id", "ASC", "bla"]'})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "too_long"
        assert violation.get("loc") == ["query", "sort"]
        assert violation.get("msg") == "Tuple should have at most 2 items after validation, not 3"

    @pytest.mark.anyio
    async def test_list_sort_invalid_direction(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"sort": '["id", "ASCC"]'})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "enum"
        assert violation.get("loc") == ["query", "sort"]
        assert violation.get("msg") == "Input should be 'ASC' or 'DESC'"

    @pytest.mark.anyio
    async def test_list_sort_invalid_attribute_name(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name()), params={"sort": '["very_unlikely_attribute_name", "ASC"]'}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "attribute_not_found"
        assert violation.get("loc") == ["query", "sort"]
        assert violation.get("msg") == "Attribute very_unlikely_attribute_name not found"
