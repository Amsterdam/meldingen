from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from meldingen.models import FormIoForm
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseUnauthorizedTest


class TestFormList(BaseUnauthorizedTest, BasePaginationParamsTest):
    ROUTE_NAME: Final[str] = "form:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_users(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        test_forms: list[FormIoForm],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result


class TestFormRetrieve:
    ROUTE_NAME: Final[str] = "form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.asyncio
    async def test_retrieve_form(self, app: FastAPI, client: AsyncClient, form: FormIoForm) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("title") == form.title
        assert data.get("display") == form.display
        assert len(data.get("components")) == len(await form.awaitable_attrs.components)

    @pytest.mark.asyncio
    async def test_retrieve_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestFormDelete(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "form:delete"
    METHOD: Final[str] = "DELETE"
    PATH_PARAMS: dict[str, Any] = {"form_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "form_title",
        [("Form #1",), ("Form #2",)],
        indirect=True,
    )
    async def test_delete_form(self, app: FastAPI, client: AsyncClient, auth_user: None, form: FormIoForm) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_form_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_unable_to_delete_primary_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, primary_form: FormIoForm
    ) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=primary_form.id))

        assert response.status_code == HTTP_404_NOT_FOUND
