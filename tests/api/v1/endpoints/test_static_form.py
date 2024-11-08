from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from meldingen.models import FormIoComponentTypeEnum, FormIoQuestionComponent, StaticForm, StaticFormTypeEnum
from tests.api.v1.endpoints.base import BaseUnauthorizedTest
from tests.api.v1.endpoints.test_form import BaseFormTest


class BaseStaticFormTest(BaseFormTest):
    async def _assert_component(self, data: dict[str, Any], component: FormIoQuestionComponent) -> None:
        await super()._assert_component(data, component)

        # Additional check, a component of a static form should have no question related to it
        assert data.get("question") is None


class TestStaticFormRetrieve(BaseStaticFormTest):
    ROUTE_NAME: Final[str] = "static-form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.anyio
    async def test_retrieve_by_id(self, app: FastAPI, client: AsyncClient, primary_form: StaticForm) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, static_form_id=primary_form.id))
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
        assert component.max_char_count == data_component.get("maxCharCount")

    @pytest.mark.anyio
    async def test_retrieve_by_id_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, static_form_id=99999))

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
                            "maxCharCount": None,
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
    async def test_update_form_with_json_logic(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        primary_form: StaticForm,
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.text_area,
                            "input": True,
                            "autoExpand": True,
                            "maxCharCount": 255,
                            "validate": {
                                "json": {
                                    "var": ["i"],
                                },
                            },
                        },
                    ],
                },
                {
                    "label": "panel-2",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.text_field,
                            "input": True,
                            "validate": {
                                "json": {
                                    "var": ["i"],
                                },
                            },
                        },
                    ],
                },
                {
                    "label": "panel-3",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.select,
                            "input": True,
                            "widget": "html5",
                            "placeholder": "This is a placeholder value",
                            "data": {
                                "values": [
                                    {"label": "label1", "value": "value1"},
                                    {"label": "label2", "value": "value2"},
                                ]
                            },
                            "validate": {
                                "json": {
                                    "var": ["i"],
                                },
                            },
                        },
                    ],
                },
                {
                    "label": "panel-4",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.checkbox,
                            "input": True,
                            "values": [
                                {"label": "label1", "value": "value1"},
                                {"label": "label2", "value": "value2"},
                            ],
                            "validate": {
                                "json": {
                                    "var": ["i"],
                                },
                            },
                        },
                    ],
                },
                {
                    "label": "panel-5",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.radio,
                            "input": True,
                            "values": [
                                {"label": "label1", "value": "value1"},
                                {"label": "label2", "value": "value2"},
                            ],
                            "validate": {
                                "json": {
                                    "var": ["i"],
                                },
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_type=primary_form.type), json=data)

        assert response.status_code == HTTP_200_OK

        body = response.json()
        components = body.get("components")
        assert len(components) == 5

        for panel in components:
            panel_components = panel.get("components")
            assert len(panel_components) == 1
            validate = panel_components[0].get("validate")
            assert validate is not None
            assert validate.get("json") == {"var": ["i"]}
            assert validate.get("required") is False

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
                            "maxCharCount": None,
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
                    "widget": "html5",
                    "placeholder": "This is a placeholder value",
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
        assert select.get("widget") == "html5"
        assert select.get("placeholder") == "This is a placeholder value"

        select_data = select.get("data")
        assert select_data is not None

        values: list[dict[str, str]] = select_data.get("values", [])
        assert len(values) == 2
        i = 1
        for value in values:
            assert value.get("label") == f"label{i}"
            assert value.get("value") == f"value{i}"
            i = i + 1


class TestStaticFormList(BaseStaticFormTest, BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "static-form:list"
    METHOD: Final[str] = "GET"

    @pytest.mark.anyio
    async def test_list_static_forms(self, app: FastAPI, client: AsyncClient, static_forms: list[StaticForm]) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME))

        assert response.status_code == HTTP_200_OK
        data = response.json()

        assert len(data) == len(static_forms)

        for form in data:

            fixture_form = next(static_form for static_form in static_forms if static_form.type == form.get("type"))

            assert form.get("title") == fixture_form.title
            assert form.get("display") == fixture_form.display

            fixture_component = fixture_form.components[0]
            data_component = form.get("components")[0]

            assert fixture_component.label == data_component.get("label")
            assert fixture_component.key == data_component.get("key")
            assert fixture_component.type == data.component.get("type")

            assert response.headers.get("content-range") == "StaticForm 0-49/4"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "title",
                SortingDirection.ASC,
                [
                    {"type": "attachments", "title": "Attachments"},
                    {"type": "contact", "title": "Contact"},
                    {"type": "location", "title": "Location"},
                    {"type": "primary", "title": "Primary"},
                ],
            ),
            (
                "title",
                SortingDirection.DESC,
                [
                    {"type": "primary", "title": "Primary"},
                    {"type": "location", "title": "Location"},
                    {"type": "contact", "title": "Contact"},
                    {"type": "attachments", "title": "Attachments"},
                ],
            ),
            (
                "id",
                SortingDirection.ASC,
                [
                    {"type": "primary", "title": "Primary"},
                    {"type": "attachments", "title": "Attachments"},
                    {"type": "location", "title": "Location"},
                    {"type": "contact", "title": "Contact"},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"type": "contact", "title": "Contact"},
                    {"type": "location", "title": "Location"},
                    {"type": "attachments", "title": "Attachments"},
                    {"type": "primary", "title": "Primary"},
                ],
            ),
            (
                "type",
                SortingDirection.ASC,
                [
                    {"type": "attachments", "title": "Attachments"},
                    {"type": "contact", "title": "Contact"},
                    {"type": "location", "title": "Location"},
                    {"type": "primary", "title": "Primary"},
                ],
            ),
            (
                "type",
                SortingDirection.DESC,
                [
                    {"type": "primary", "title": "Primary"},
                    {"type": "location", "title": "Location"},
                    {"type": "contact", "title": "Contact"},
                    {"type": "attachments", "title": "Attachments"},
                ],
            ),
        ],
    )
    async def test_list_static_forms_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        static_forms: list[StaticForm],
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, params={"sort": f"{attribute}:{direction}"}))

        assert response.status_code == HTTP_200_OK
        data = response.json()

        assert len(data) == len(static_forms)
        assert response.headers.get("content-range") == "StaticForm 0-49/4"

        for i in range(len(expected)):
            assert data[i].get("type") == expected[i].get("type")
            assert data[i].get("title") == expected[i].get("title")
