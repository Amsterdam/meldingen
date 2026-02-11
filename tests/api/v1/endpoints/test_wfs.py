from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, HTTPStatusError, Response
from meldingen_core.wfs import BaseWfsProviderFactory, InvalidWfsProviderException
from starlette.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
)

from meldingen.models import AssetType
from meldingen.wfs import ProxyWfsProvider, UrlProcessor


class ValidMockProxyWfsProviderFactory(BaseWfsProviderFactory):
    def __call__(self) -> ProxyWfsProvider:
        response = Mock(Response)
        response.status_code = 200

        http_client = AsyncMock(AsyncClient)
        http_client.stream.return_value.__aenter__.return_value = response

        return ProxyWfsProvider(self._arguments["base_url"], UrlProcessor(), http_client)

    async def validate(self) -> None:
        if "base_url" not in self._arguments:
            raise InvalidWfsProviderException("Missing 'base_url' in arguments")


class FailingHttpWfsProviderFactory(BaseWfsProviderFactory):
    """A WFS provider factory that simulates an upstream HTTP error."""

    def __call__(self) -> ProxyWfsProvider:
        mock_response = Mock(Response)
        mock_response.status_code = 500

        http_client = AsyncMock(AsyncClient)
        http_client.send.return_value = mock_response
        http_client.send.return_value.raise_for_status.side_effect = HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        return ProxyWfsProvider(self._arguments["base_url"], UrlProcessor(), http_client)

    async def validate(self) -> None:
        pass


@pytest.mark.anyio
@pytest.mark.parametrize(
    "asset_type_name, asset_type_class_name, asset_type_arguments",
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
        return "asset-type:retrieve-wfs"

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
        response = await client.get(app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id))
        assert response.status_code == HTTP_200_OK

    @pytest.mark.anyio
    async def test_retrieve_wfs_non_existing_asset_type(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id + 1))
        status = response.status_code

        assert status == HTTP_404_NOT_FOUND
        assert "AssetType not found" in response.content.decode()

    @pytest.mark.anyio
    async def test_retrieve_wfs_invalid_query_params(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), asset_type_id=asset_type.id), params={"service": "NotWfs"}
        )
        status = response.status_code
        content = response.json()
        detail = content.get("detail")

        assert status == HTTP_422_UNPROCESSABLE_CONTENT
        assert detail[0].get("msg") == "Input should be 'WFS'"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "asset_type_name, asset_type_class_name, asset_type_arguments",
    [("invalid_provider", "nonexistent.module.Class", {})],
)
class TestRetrieveWfsInvalidProvider:
    @pytest.mark.anyio
    async def test_retrieve_wfs_invalid_provider_returns_500(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for("asset-type:retrieve-wfs", asset_type_id=asset_type.id))

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to find module" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "asset_type_name, asset_type_class_name, asset_type_arguments",
    [
        (
            "failing_http",
            "tests.api.v1.endpoints.test_wfs.FailingHttpWfsProviderFactory",
            {"base_url": "https://example.com"},
        )
    ],
)
class TestRetrieveWfsUpstreamError:
    @pytest.mark.anyio
    async def test_retrieve_wfs_upstream_error_returns_502(
        self, app: FastAPI, client: AsyncClient, asset_type: AssetType, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for("asset-type:retrieve-wfs", asset_type_id=asset_type.id))

        assert response.status_code == HTTP_502_BAD_GATEWAY
