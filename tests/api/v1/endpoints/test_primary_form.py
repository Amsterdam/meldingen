from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from meldingen.models import FormIoComponentTypeEnum, FormIoForm, FormIoPrimaryForm
from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestPrimaryFormRetrieve:
    ROUTE_NAME: Final[str] = "primary-form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.asyncio
    async def test_retrieve_primary_form(
        self, app: FastAPI, client: AsyncClient, primary_form: FormIoPrimaryForm
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("title") == primary_form.title
        assert data.get("display") == primary_form.display
        assert len(data.get("components")) == len(await primary_form.awaitable_attrs.components)

    @pytest.mark.asyncio
    async def test_retrieve_primary_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_retrieve_primary_form_other_form_exists(
        self, app: FastAPI, client: AsyncClient, form: FormIoForm
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestPrimaryFormUpdate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "primary-form:update"
    METHOD: Final[str] = "PUT"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
    async def test_update_primary_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: FormIoPrimaryForm,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "components": [
                {
                    "label": "klacht",
                    "description": "Wat is uw klacht?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "panel-1",
                    "description": "Panel #1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "autoExpand": False,
                    "showCharCount": False,
                    "components": [
                        {
                            "label": "aanvullend",
                            "description": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                            "key": "textArea",
                            "type": "textArea",
                            "input": True,
                            "autoExpand": True,
                            "showCharCount": True,
                        },
                    ],
                },
            ],
        }

        assert primary_form.title != new_data["title"]
        primary_form_components = await primary_form.awaitable_attrs.components
        assert len(primary_form_components) != len(new_data["components"])

        response = await client.put(app.url_path_for(self.ROUTE_NAME), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data["title"] == new_data["title"]
        assert data["display"] == "form"
        assert len(data["components"]) == len(new_data["components"])
