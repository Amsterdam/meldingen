from typing import Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY

from meldingen.models import FormIoForm, FormIoPrimaryForm
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
                    "label": "Wat is uw klacht?",
                    "description": "",
                    "key": "wat-is-uw-klacht",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                            "description": "Help tekst bij de vraag.",
                            "key": "heeft-u-no-aanvullend",
                            "type": "textarea",
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

    @pytest.mark.asyncio
    async def test_update_no_primary_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "components": [
                {
                    "label": "Wat is uw klacht?",
                    "description": "",
                    "key": "wat-is-uw-klacht",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                            "description": "Help tekst bij de vraag.",
                            "key": "heeft-u-no-aanvullend",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "showCharCount": True,
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME), json=new_data)

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_primary_form_invalid_nesting(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        data = {
            "title": "Formulier #1",
            "components": [
                {
                    "label": "Wat is uw klacht?",
                    "description": "",
                    "key": "wat-is-uw-klacht",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                    "components": [
                        {
                            "label": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                            "description": "Help tekst bij de vraag.",
                            "key": "heeft-u-no-aanvullend",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "showCharCount": True,
                        },
                    ],
                }
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "extra_forbidden"
        assert violation.get("loc") == ["body", "components", 0, "component", "components"]
        assert violation.get("msg") == "Extra inputs are not permitted"
        assert violation.get("input") == [
            {
                "label": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                "description": "Help tekst bij de vraag.",
                "key": "heeft-u-no-aanvullend",
                "type": "textarea",
                "input": True,
                "autoExpand": True,
                "showCharCount": True,
            },
        ]

    @pytest.mark.asyncio
    async def test_update_primary_form_invalid_nesting_panel_with_panel(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "panel-2",
                            "key": "panel",
                            "type": "panel",
                            "input": False,
                            "components": [
                                {
                                    "label": "Heeft u nog aanvullende informatie die belangrijk kan zijn voor ons?",
                                    "description": "Help tekst bij de vraag.",
                                    "key": "heeft-u-no-aanvullend",
                                    "type": "textarea",
                                    "input": True,
                                    "autoExpand": False,
                                    "showCharCount": False,
                                }
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 5

        # The import error
        violation = detail[1]
        assert violation.get("type") == "assertion_error"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "type"]
        assert violation.get("msg") == "Assertion failed, panel is not allowed"

        # The additional errors
        violation = detail[0]
        assert violation.get("type") == "missing"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "description"]
        assert violation.get("msg") == "Field required"

        violation = detail[2]
        assert violation.get("type") == "missing"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "autoExpand"]
        assert violation.get("msg") == "Field required"

        violation = detail[3]
        assert violation.get("type") == "missing"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "showCharCount"]
        assert violation.get("msg") == "Field required"

        violation = detail[4]
        assert violation.get("type") == "extra_forbidden"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "components"]
        assert violation.get("msg") == "Extra inputs are not permitted"
