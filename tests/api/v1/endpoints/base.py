from abc import ABCMeta, abstractmethod
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_401_UNAUTHORIZED


class BaseUnauthorizedTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @abstractmethod
    def get_method(self) -> str: ...

    def get_path_params(self) -> dict[str, Any]:
        return {}

    @pytest.mark.asyncio
    async def test_unauthorized(self, app: FastAPI, client: AsyncClient) -> None:
        """Tests that a 401 response is given when no access token is provided through the Authorization header."""
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data.get("detail") == "Not authenticated"
