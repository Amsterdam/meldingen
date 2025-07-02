import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestRetrieveContainerAsset(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "asset:retrieve"

    def get_method(self) -> str:
        return "GET"

    def get_asset_type_create_route_name(self) -> str:
        return "asset-type:create"

    @pytest.mark.anyio
    async def test_retrieve_asset(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        await client.post(
            app.url_path_for(self.get_asset_type_create_route_name()),
            json={
                "name": "container",
                "class_name": "meldingen.api.v1.endpoints.asset.ContainerWfsClient",
                "arguments": {"base_url": "https://example.com"},
            },
        )

        response = await client.get(app.url_path_for(self.get_route_name(), name="container"))

        assert "Example Domain" in str(response.content)
