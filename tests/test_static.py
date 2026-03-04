import pytest
from fastapi import FastAPI
from httpx import AsyncClient


class TestStatic:
    @pytest.mark.anyio
    async def test_get_robots_txt(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get("/robots.txt")

        assert response.status_code == 200
        assert "User-agent: *" in response.text
        assert "Disallow: /" in response.text
