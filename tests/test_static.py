import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestCreateAssetType(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "static:robots"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_get_robots_txt(self, app: FastAPI, client: AsyncClient):
        response = await client.request(self.get_method(), self.get_route_name())

        assert response.status_code == 200
        assert "User-agent: *" in response.text
        assert "Disallow: /admin" in response.text
