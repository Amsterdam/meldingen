from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from meldingen_core.wfs import BaseWfsProviderFactory
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.models import AssetType
from meldingen.wfs import ProxyWfsProvider, UrlProcessor


class ValidMockProxyWfsProviderFactory(BaseWfsProviderFactory):
    _base_url: str

    def __init__(self, base_url: str):
        self._base_url = base_url

    def __call__(self) -> ProxyWfsProvider:
        response = Mock(Response)
        response.status_code = 200

        http_client = AsyncMock(AsyncClient)
        http_client.stream.return_value.__aenter__.return_value = response

        return ProxyWfsProvider(self._base_url, UrlProcessor(), http_client)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "asset_type_name, asset_type_class_name, arguments",
    [
        (
            "container",
            "tests.api.v1.endpoints.test_wfs.ValidMockProxyWfsProviderFactory",
            {"base_url": "https://example.com"},
        )
    ],
)
class TestRetrieveContainerWfs:
    def get_route_name(self) -> str:
        return "wfs:retrieve"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return {"name": "container"}

    def get_asset_type_create_route_name(self) -> str:
        return "asset-type:create"

    @pytest.mark.anyio
    async def test_retrieve_wfs(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name(), name=asset_type.name))
        assert response.status_code == HTTP_200_OK

    @pytest.mark.anyio
    async def test_retrieve_wfs_non_existing_asset_type(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name(), name=asset_type.name + "-incorrect-name"))
        status = response.status_code

        assert status == HTTP_404_NOT_FOUND
        assert "AssetType not found" in response.content.decode()

    @pytest.mark.anyio
    async def test_retrieve_wfs_invalid_query_params(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), name=asset_type.name), params={"service": "NotWfs"}
        )
        status = response.status_code
        content = response.json()
        detail = content.get("detail")

        assert status == HTTP_422_UNPROCESSABLE_ENTITY
        assert detail[0].get("msg") == "Input should be 'WFS'"
