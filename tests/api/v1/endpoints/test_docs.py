from typing import Final

from fastapi import FastAPI
from httpx import AsyncClient


class TestScalarEndpoint:
    ROUTE_NAME: Final[str] = "docs:scalar"

    async def test_scalar_endpoint_returns_html_with_title(self, app: FastAPI, client: AsyncClient):
        response = await client.get(app.url_path_for(self.ROUTE_NAME))
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"].lower()
        assert "Meldingen API Reference" in response.text
