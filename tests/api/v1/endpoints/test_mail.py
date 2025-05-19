import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK

from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestMailPreview(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "mail:preview"

    def get_method(self) -> str:
        return "POST"

    @pytest.mark.anyio
    async def test_preview_mail_action(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name()),
            json={"title": "Test Title", "preview_text": "Test Preview Text", "body_text": "Test Body"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text
