import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestRetrieveContainerAsset(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset:container:retrieve"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_asset_type_create(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for(self.get_route_name()))

        print(response)
