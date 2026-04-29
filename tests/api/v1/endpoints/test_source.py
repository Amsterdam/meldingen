import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import HTTP_200_OK

from meldingen.models import Source
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestSourceList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    def get_route_name(self) -> str:
        return "source:list"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_list_all_sources(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_sources: list[Source]
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == len(initial_sources)
        assert {item["name"] for item in data} == {source.name for source in initial_sources}
        assert response.headers.get("content-range") == f"source 0-49/{len(initial_sources)}"

    @pytest.mark.anyio
    async def test_list_sources_empty(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        assert response.status_code == HTTP_200_OK
        assert response.json() == []
        assert response.headers.get("content-range") == "source 0-49/0"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected",
        [(2, 0, 2), (3, 0, 3), (10, 6, 0), (1, 5, 1)],
    )
    async def test_list_sources_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        initial_sources: list[Source],
        limit: int,
        offset: int,
        expected: int,
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == expected
        assert response.headers.get("content-range") == f"source {offset}-{limit - 1 + offset}/{len(initial_sources)}"

    @pytest.mark.anyio
    async def test_list_sources_sorted_by_name(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_sources: list[Source]
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name()), params={"sort": f'["name", "{SortingDirection.ASC}"]'}
        )

        assert response.status_code == HTTP_200_OK
        names = [item["name"] for item in response.json()]
        assert names == sorted(source.name for source in initial_sources)

    @pytest.mark.anyio
    async def test_list_sources_filtered_by_q(
        self, app: FastAPI, client: AsyncClient, auth_user: None, initial_sources: list[Source]
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()), params={"filter": '{"q": "Telefoon"}'})

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Telefoon"
        assert response.headers.get("content-range") == "source 0-49/1"
