import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_404_NOT_FOUND

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestRetrieveContainerWfs(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "wfs:retrieve"

    def get_method(self) -> str:
        return "GET"

    def get_asset_type_create_route_name(self) -> str:
        return "asset-type:create"

    @pytest.mark.anyio
    async def test_retrieve_wfs(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        await client.post(
            app.url_path_for(self.get_asset_type_create_route_name()),
            json={
                "name": "container",
                "class_name": "meldingen.wfs.ProxyWfsProvider",
                "arguments": {"base_url": "https://example.com"},
            },
        )

        response = await client.get(app.url_path_for(self.get_route_name(), name="container"))
        content = response.content

        assert "Example Domain" in str(content)

    @pytest.mark.anyio
    async def test_retrieve_wfs_non_existing_asset_type(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        await client.post(
            app.url_path_for(self.get_asset_type_create_route_name()),
            json={
                "name": "this does not exist",
                "class_name": "meldingen.wfs.ProxyWfsProvider",
                "arguments": {"base_url": "https://example.com"},
            },
        )

        response = await client.get(app.url_path_for(self.get_route_name(), name="container"))
        status = response.status_code

        assert status == HTTP_404_NOT_FOUND
        assert "AssetType not found" in response.content.decode()
