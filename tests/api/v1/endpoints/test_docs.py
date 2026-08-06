from typing import Final

from fastapi import FastAPI
from httpx import AsyncClient

from meldingen.api.v1.endpoints.docs import SCALAR_JS_URL


class TestScalarEndpoint:
    ROUTE_NAME: Final[str] = "docs:scalar"

    async def test_scalar_endpoint_returns_html_with_title(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"].lower()
        assert "Meldingen API Reference" in response.text

    async def test_scalar_endpoint_loads_a_pinned_frontend(self, app: FastAPI, client: AsyncClient) -> None:
        """An unpinned CDN URL lets a Scalar release break OAuth without a deploy."""
        response = await client.get(app.url_path_for(self.ROUTE_NAME))
        assert f'<script src="{SCALAR_JS_URL}">' in response.text
        assert "@scalar/api-reference@" in SCALAR_JS_URL
