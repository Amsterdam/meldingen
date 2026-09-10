import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_422_UNPROCESSABLE_CONTENT

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

    @pytest.mark.anyio
    async def test_preview_mail_rejects_body_with_disallowed_link_scheme(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        # The preview is rendered in a browser, so the body must not reach the renderer with an
        # href the browser would execute.
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name()),
            json={
                "title": "Test Title",
                "preview_text": "Test Preview Text",
                "body_text": "[Klik hier voor meer informatie](javascript:alert(1))",
            },
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
