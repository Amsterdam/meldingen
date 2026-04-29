import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import HTTP_200_OK

from meldingen.models import Label
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestLabelList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    def get_route_name(self) -> str:
        return "label:list"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_list_all_labels(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_labels: list[Label]
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == len(initial_labels)
        assert {item["name"] for item in data} == {label.name for label in initial_labels}
        assert response.headers.get("content-range") == f"label 0-49/{len(initial_labels)}"

    @pytest.mark.anyio
    async def test_list_labels_empty(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        assert response.status_code == HTTP_200_OK
        assert response.json() == []
        assert response.headers.get("content-range") == "label 0-49/0"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected",
        [(2, 0, 2), (3, 0, 3), (10, 6, 0), (1, 5, 1)],
    )
    async def test_list_labels_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        initial_labels: list[Label],
        limit: int,
        offset: int,
        expected: int,
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == expected
        assert response.headers.get("content-range") == f"label {offset}-{limit - 1 + offset}/{len(initial_labels)}"

    @pytest.mark.anyio
    async def test_list_labels_sorted_by_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_labels: list[Label]
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name()), params={"sort": f'["name", "{SortingDirection.ASC}"]'}
        )

        assert response.status_code == HTTP_200_OK
        names = [item["name"] for item in response.json()]
        assert names == sorted(label.name for label in initial_labels)

    @pytest.mark.anyio
    async def test_list_labels_filtered_by_q(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_labels: list[Label]
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"filter": '{"q": "Klacht"}'})

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Klacht"
        assert response.headers.get("content-range") == "label 0-49/1"
