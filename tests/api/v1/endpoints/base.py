import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_401_UNAUTHORIZED


class UnauthorizedMixin:
    @pytest.mark.asyncio
    async def test_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.request(self.METHOD, app.url_path_for(self.ROUTE_NAME), json={})

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"
