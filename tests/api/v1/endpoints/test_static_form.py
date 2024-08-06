from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from meldingen.models import FormIoComponentTypeEnum, FormIoQuestionComponent, StaticForm, StaticFormTypeEnum
from tests.api.v1.endpoints.base import BaseUnauthorizedTest
from tests.api.v1.endpoints.test_form import BaseFormTest


class BaseStaticFormTest(BaseFormTest):
    async def _assert_component(self, data: dict[str, Any], component: FormIoQuestionComponent) -> None:
        await super()._assert_component(data, component)

        # Additional check, a component of a static form should have no question related to it
        assert data.get("question") is None


class TestStaticFormRetrieveByType(BaseStaticFormTest):
    ROUTE_NAME: Final[str] = "static-form:retrieve-by-type"
    METHOD: Final[str] = "GET"

    @pytest.mark.anyio
    async def test_retrieve_primary_form(self, app: FastAPI, client: AsyncClient, primary_form: StaticForm) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_type=StaticFormTypeEnum.primary))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("type") == primary_form.type
        assert data.get("title") == primary_form.title
        assert data.get("display") == primary_form.display
        assert data.get("created_at") == primary_form.created_at.isoformat()
        assert data.get("updated_at") == primary_form.updated_at.isoformat()

        components = await primary_form.awaitable_attrs.components
        assert len(data.get("components")) == len(components)

        component = components[0]
        data_component = data.get("components")[0]

        assert component.label == data_component.get("label")
        assert component.description == data_component.get("description")
        assert component.key == data_component.get("key")
        assert component.type == data_component.get("type")
        assert component.input == data_component.get("input")
        assert component.auto_expand == data_component.get("autoExpand")
        assert component.show_char_count == data_component.get("showCharCount")

    @pytest.mark.anyio
    async def test_retrieve_primary_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_type=StaticFormTypeEnum.primary))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestStaticFormUpdate(BaseUnauthorizedTest, BaseFormTest):
    ROUTE_NAME: Final[str] = "static-form:update"
    METHOD: Final[str] = "PUT"
    PATH_PARAMS: dict[str, Any] = {"form_type": StaticFormTypeEnum.primary}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.anyio
    async def test_update_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: StaticForm,
    ) -> None:
        new_data = {
            "title": "1. Beschrijf uw melding",
            "display": "wizard",
            "components": [
                {
                    "label": "panel-1",
                    "key": "panel-1",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waar gaat het over?",
                            "description": "Typ geen persoonsgegevens in deze omschrijving. We vragen dit later in dit formulier aan u.",
                            "key": "waar-gaat-het-over",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": False,
                            "showCharCount": False,
                        }
                    ],
                }
            ],
        }

        assert primary_form.title != new_data["title"]
        assert primary_form.display != new_data["display"]

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_type=primary_form.type), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("type") == primary_form.type
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = await primary_form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_with_text_field(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: StaticForm,
    ) -> None:
        new_data = {
            "title": "1. Beschrijf uw melding",
            "display": "wizard",
            "components": [
                {
                    "label": "Waar gaat het over?",
                    "description": "Typ geen persoonsgegevens in deze omschrijving. We vragen dit later in dit formulier aan u.",
                    "key": "waar-gaat-het-over",
                    "type": FormIoComponentTypeEnum.text_field,
                    "input": True,
                }
            ],
        }

        assert primary_form.title != new_data["title"]
        assert primary_form.display != new_data["display"]

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_type=primary_form.type), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("type") == primary_form.type
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = await primary_form.awaitable_attrs.components
        assert len(data.get("components")) == len(components)

        component = components[0]
        data_component = data.get("components")[0]

        assert component.label == data_component.get("label")
        assert component.description == data_component.get("description")
        assert component.key == data_component.get("key")
        assert component.type == data_component.get("type")
        assert component.input == data_component.get("input")

    @pytest.mark.anyio
    async def test_update_primary_form_does_not_exists(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
    ) -> None:
        new_data = {
            "title": "1. Beschrijf uw melding",
            "display": "wizard",
            "components": [
                {
                    "label": "panel-1",
                    "key": "panel-1",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waar gaat het over?",
                            "description": "Typ geen persoonsgegevens in deze omschrijving. We vragen dit later in dit formulier aan u.",
                            "key": "waar-gaat-het-over",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": False,
                            "showCharCount": False,
                        }
                    ],
                }
            ],
        }
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, form_type=StaticFormTypeEnum.primary), json=new_data
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_form_values(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: StaticForm,
    ) -> None:
        new_data = {
            "title": "1. Beschrijf uw melding",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": "radio",
                    "input": True,
                    "values": [
                        {
                            "label": "Ja",
                            "value": "yes",
                        },
                        {
                            "label": "Nee",
                            "value": "no",
                        },
                    ],
                },
                {
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Selecteer een optie?",
                            "description": "",
                            "key": "selecteer-een-optie",
                            "type": "selectboxes",
                            "input": True,
                            "values": [
                                {
                                    "label": "Optie #1",
                                    "value": "option-1",
                                },
                                {
                                    "label": "Optie #2",
                                    "value": "option-2",
                                },
                                {
                                    "label": "Optie #3",
                                    "value": "option-3",
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_type=primary_form.type), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        components = await primary_form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_with_select(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: StaticForm,
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "label": "Waarom meld u dit bij ons?",
                    "description": "",
                    "key": "waarom-meld-u-dit-bij-ons",
                    "type": FormIoComponentTypeEnum.select,
                    "input": True,
                    "data": {
                        "values": [
                            {"label": "label1", "value": "value1"},
                            {"label": "label2", "value": "value2"},
                        ]
                    },
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_type=primary_form.type), json=data)

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("type") == primary_form.type
        assert body.get("title") == "Formulier #1"
        assert body.get("display") == "form"

        components = body.get("components")
        assert len(components) == 1

        select = components[0]
        assert select.get("label") == "Waarom meld u dit bij ons?"
        assert select.get("description") == ""
        assert select.get("key") == "waarom-meld-u-dit-bij-ons"
        assert select.get("type") == FormIoComponentTypeEnum.select
        assert select.get("input") is True

        select_data = select.get("data")
        assert select_data is not None

        values: list[dict[str, str]] = select_data.get("values", [])
        assert len(values) == 2
        i = 1
        for value in values:
            assert value.get("label") == f"label{i}"
            assert value.get("value") == f"value{i}"
            i = i + 1
