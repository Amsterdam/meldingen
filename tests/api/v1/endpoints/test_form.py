from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from meldingen.models import (
    Classification,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponentTypeEnum,
    FormIoComponentValue,
    FormIoDateComponent,
    FormIoPanelComponent,
    FormIoQuestionComponent,
    FormIoRadioComponent,
    FormIoTextAreaComponent,
)
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class BaseFormTest:
    async def _assert_components(
        self,
        data: list[dict[str, Any]],
        components: list[
            FormIoPanelComponent | FormIoQuestionComponent | FormIoCheckBoxComponent | FormIoRadioComponent
        ],
    ) -> None:
        assert len(data) == len(components)

        for component in components:
            component_data = data[component.position - 1]
            if component.type == FormIoComponentTypeEnum.panel:
                assert isinstance(component, FormIoPanelComponent)
                await self._assert_panel_component(component_data, component)
            elif component.type in [FormIoComponentTypeEnum.checkbox, FormIoComponentTypeEnum.radio]:
                assert isinstance(component, (FormIoCheckBoxComponent, FormIoRadioComponent))
                await self._assert_value_component(component_data, component)
            elif component.type == FormIoComponentTypeEnum.date:
                assert isinstance(component, FormIoDateComponent)
                await self._assert_date_component(component_data, component)
            else:
                assert isinstance(component, FormIoQuestionComponent)
                await self._assert_component(component_data, component)

    async def _assert_panel_component(self, data: dict[str, Any], component: FormIoPanelComponent) -> None:
        assert data.get("title") == component.title
        assert data.get("label") == component.label
        assert data.get("key") == component.key
        assert data.get("type") == component.type
        assert data.get("input") == component.input
        assert data.get("conditional") == component.conditional

        component_data = data.get("components", [])
        assert isinstance(component_data, list)  # This is here for mypy

        components = await component.awaitable_attrs.components
        if components:
            await self._assert_components(component_data, components)

    async def _assert_component_values(self, data: list[dict[str, Any]], values: list[FormIoComponentValue]) -> None:
        assert len(data) == len(values)

        for value in values:
            value_data = data[value.position - 1]
            assert value_data.get("label") == value.label
            assert value_data.get("value") == value.value

    async def _assert_value_component(
        self, data: dict[str, Any], component: FormIoCheckBoxComponent | FormIoRadioComponent
    ) -> None:
        assert data.get("label") == component.label
        assert data.get("key") == component.key
        assert data.get("type") == component.type
        assert data.get("input") == component.input
        assert data.get("conditional") == component.conditional

        values_data = data.get("values", [])
        assert isinstance(values_data, list)  # This is here for mypy

        values = await component.awaitable_attrs.values
        if values:
            await self._assert_component_values(values_data, values)

    async def _assert_date_component(self, data: dict[str, Any], component: FormIoDateComponent) -> None:
        assert data.get("dayRange") == component.day_range
        await self._assert_component(data, component)

    async def _assert_component(self, data: dict[str, Any], component: FormIoQuestionComponent) -> None:
        assert data.get("label") == component.label
        assert data.get("description") == component.description
        assert data.get("key") == component.key
        assert data.get("type") == component.type
        assert data.get("input") == component.input

        assert data.get("position") == component.position
        assert data.get("question") == component.question_id
        assert data.get("conditional") == component.conditional

        validate = data.get("validate")
        assert validate is not None

        # Some component fixtures do not have required set,
        # then it defaults to None while the output is always a boolean
        if component.required is not None:
            assert validate.get("required") == component.required
            assert validate.get("required_error_message") == component.required_error_message

        if isinstance(component, FormIoTextAreaComponent):
            assert data.get("autoExpand") == component.auto_expand
            assert data.get("maxCharCount") == component.max_char_count


class TestFormList(BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "form:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(10, 0, 10), (5, 0, 5), (10, 10, 0), (1, 10, 0)],
    )
    async def test_list_forms_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        forms: list[Form],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        for form in data:
            assert form.get("classification", "") is None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, expected_result",
        [(11, 0, 11), (5, 0, 5)],
    )
    async def test_list_forms_first_with_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form_with_classification: Form,
        limit: int,
        offset: int,
        expected_result: int,
        forms: list[Form],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert data[0].get("classification", "") == form_with_classification.classification_id
        for form in data[1:]:
            assert form.get("classification", "") is None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/11"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"title": "Form #1", "display": "form", "classification": None},
                    {"title": "Form #2", "display": "form", "classification": None},
                    {"title": "Form #3", "display": "form", "classification": None},
                    {"title": "Form #4", "display": "form", "classification": None},
                    {"title": "Form #5", "display": "form", "classification": None},
                    {"title": "Form #6", "display": "form", "classification": None},
                    {"title": "Form #7", "display": "form", "classification": None},
                    {"title": "Form #8", "display": "form", "classification": None},
                    {"title": "Form #9", "display": "form", "classification": None},
                    {"title": "Form #10", "display": "form", "classification": None},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"title": "Form #10", "display": "form", "classification": None},
                    {"title": "Form #9", "display": "form", "classification": None},
                    {"title": "Form #8", "display": "form", "classification": None},
                    {"title": "Form #7", "display": "form", "classification": None},
                    {"title": "Form #6", "display": "form", "classification": None},
                    {"title": "Form #5", "display": "form", "classification": None},
                    {"title": "Form #4", "display": "form", "classification": None},
                    {"title": "Form #3", "display": "form", "classification": None},
                    {"title": "Form #2", "display": "form", "classification": None},
                    {"title": "Form #1", "display": "form", "classification": None},
                ],
            ),
            (
                "title",
                SortingDirection.ASC,
                [
                    {"title": "Form #1", "display": "form", "classification": None},
                    {"title": "Form #10", "display": "form", "classification": None},
                    {"title": "Form #2", "display": "form", "classification": None},
                    {"title": "Form #3", "display": "form", "classification": None},
                    {"title": "Form #4", "display": "form", "classification": None},
                    {"title": "Form #5", "display": "form", "classification": None},
                    {"title": "Form #6", "display": "form", "classification": None},
                    {"title": "Form #7", "display": "form", "classification": None},
                    {"title": "Form #8", "display": "form", "classification": None},
                    {"title": "Form #9", "display": "form", "classification": None},
                ],
            ),
            (
                "title",
                SortingDirection.DESC,
                [
                    {"title": "Form #9", "display": "form", "classification": None},
                    {"title": "Form #8", "display": "form", "classification": None},
                    {"title": "Form #7", "display": "form", "classification": None},
                    {"title": "Form #6", "display": "form", "classification": None},
                    {"title": "Form #5", "display": "form", "classification": None},
                    {"title": "Form #4", "display": "form", "classification": None},
                    {"title": "Form #3", "display": "form", "classification": None},
                    {"title": "Form #2", "display": "form", "classification": None},
                    {"title": "Form #10", "display": "form", "classification": None},
                    {"title": "Form #1", "display": "form", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_forms_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        forms: list[Form],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["title"] == expected[i]["title"]
            assert data[i]["display"] == expected[i]["display"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "form 0-49/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "title",
                SortingDirection.DESC,
                [
                    {"title": "Form #7", "display": "form", "classification": None},
                    {"title": "Form #6", "display": "form", "classification": None},
                ],
            ),
            (
                3,
                1,
                "title",
                SortingDirection.ASC,
                [
                    {"title": "Form #10", "display": "form", "classification": None},
                    {"title": "Form #2", "display": "form", "classification": None},
                    {"title": "Form #3", "display": "form", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_forms_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        forms: list[Form],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["title"] == expected[i]["title"]
            assert data[i]["display"] == expected[i]["display"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/10"


class TestFormRetrieve(BaseFormTest):
    ROUTE_NAME: Final[str] = "form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.anyio
    async def test_retrieve_form(self, app: FastAPI, client: AsyncClient, form: Form) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form.id
        assert data.get("title") == form.title
        assert data.get("display") == form.display
        assert data.get("created_at") == form.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert data.get("updated_at") == form.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        await self._assert_components(data.get("components"), await form.awaitable_attrs.components)

    @pytest.mark.anyio
    async def test_retrieve_form_with_classification(
        self, app: FastAPI, client: AsyncClient, form_with_classification: Form
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form_with_classification.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form_with_classification.id
        assert data.get("title") == form_with_classification.title
        assert data.get("display") == form_with_classification.display
        assert len(data.get("components")) == len(await form_with_classification.awaitable_attrs.components)
        assert data.get("classification") == form_with_classification.classification_id

    @pytest.mark.anyio
    async def test_retrieve_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.anyio
    async def test_retrieve_form_with_date_component(
        self, app: FastAPI, client: AsyncClient, form_with_date_component: Form
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form_with_date_component.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form_with_date_component.id
        assert data.get("title") == form_with_date_component.title
        assert data.get("display") == form_with_date_component.display
        assert len(data.get("components")) == len(await form_with_date_component.awaitable_attrs.components)

        await self._assert_components(data.get("components"), await form_with_date_component.awaitable_attrs.components)

    @pytest.mark.anyio
    async def test_retrieve_form_with_time_component(
        self, app: FastAPI, client: AsyncClient, form_with_time_component: Form
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form_with_time_component.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form_with_time_component.id
        assert data.get("title") == form_with_time_component.title
        assert data.get("display") == form_with_time_component.display
        assert len(data.get("components")) == len(await form_with_time_component.awaitable_attrs.components)

        await self._assert_components(data.get("components"), await form_with_time_component.awaitable_attrs.components)


class TestFormDelete(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "form:delete"
    METHOD: Final[str] = "DELETE"
    PATH_PARAMS: dict[str, Any] = {"form_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "form_title",
        [("Form #1",), ("Form #2",)],
        indirect=True,
    )
    async def test_delete_form(self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.anyio
    async def test_delete_form_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestFormUpdate(BaseUnauthorizedTest, BaseFormTest):
    ROUTE_NAME: Final[str] = "form:update"
    METHOD: Final[str] = "PUT"
    PATH_PARAMS: dict[str, Any] = {"form_id": 1}

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
        form: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "maxCharCount": 255,
                        },
                    ],
                },
            ],
        }

        assert form.title != new_data["title"]
        assert form.display != new_data["display"]
        form_components = await form.awaitable_attrs.components
        assert len(form_components) != len(new_data["components"])

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("id") == form.id
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = await form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_with_jsonlogic(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "title": "Panel 1 title",
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
                                    "==": [1, 1],
                                },
                            },
                        },
                    ],
                },
                {
                    "title": "Panel 2 title",
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
                                    "==": [1, 1],
                                },
                            },
                        },
                    ],
                },
                {
                    "title": "Panel 3 title",
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
                                    "==": [1, 1],
                                },
                            },
                        },
                    ],
                },
                {
                    "title": "Panel 4 title",
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
                                    "==": [1, 1],
                                },
                            },
                        },
                    ],
                },
                {
                    "title": "Panel 5 title",
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
                                    "==": [1, 1],
                                },
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=data)
        assert response.status_code == HTTP_200_OK

        body = response.json()
        components = body.get("components")
        assert len(components) == 5

        for panel in components:
            panel_components = panel.get("components")
            assert len(panel_components) == 1
            validate = panel_components[0].get("validate")
            assert validate is not None
            assert validate.get("json") == {"==": [1, 1]}
            assert validate.get("required") is False

    @pytest.mark.anyio
    async def test_update_form_with_new_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
        classification: Classification,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "classification": classification.id,
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "maxCharCount": 255,
                },
                {
                    "label": "Waarom meld u dit bij ons?",
                    "description": "",
                    "key": "waarom-meld-u-dit-bij-ons",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "maxCharCount": 255,
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("id") == form.id
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("classification", "") == classification.id

        components = await form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_change_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form_with_classification: Form,
        classification: Classification,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "classification": classification.id,
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "maxCharCount": 255,
                },
                {
                    "label": "Waarom meld u dit bij ons?",
                    "description": "",
                    "key": "waarom-meld-u-dit-bij-ons",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "maxCharCount": 255,
                },
            ],
        }

        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, form_id=form_with_classification.id), json=new_data
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("id") == form_with_classification.id
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("classification", "") == classification.id

        components = await form_with_classification.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_with_classification_that_does_not_exist(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "classification": 123456,
            "components": [],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "Classification not found"

    @pytest.mark.anyio
    async def test_update_form_remove_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form_with_classification: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "classification": None,
            "components": [],
        }

        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, form_id=form_with_classification.id), json=new_data
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification", "") is None

    @pytest.mark.anyio
    async def test_update_form_assign_classification_that_is_already_assigned_to_another_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
        form_with_classification: Form,
    ) -> None:
        classification = await form_with_classification.awaitable_attrs.classification
        new_data = {
            "title": "Form",
            "display": "form",
            "classification": classification.id,
            "components": [
                {
                    "label": "Wat is uw klacht?",
                    "description": "",
                    "key": "wat-is-uw_klacht",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "maxCharCount": 255,
                }
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification") == classification.id

    @pytest.mark.anyio
    async def test_update_form_classification_id_validation(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "classification": 0,
            "components": [],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than"
        assert violation.get("loc") == ["body", "classification"]
        assert violation.get("msg") == "Input should be greater than 0"

    @pytest.mark.anyio
    async def test_update_form_invalid_nesting_panel_with_panel(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "title": "Panel 2 title",
                            "label": "panel-2",
                            "key": "panel",
                            "type": "panel",
                            "input": False,
                            "components": [
                                {
                                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                                    "description": "Help tekst bij de vraag.",
                                    "key": "heeft-u-meer-informatie",
                                    "type": "textarea",
                                    "input": True,
                                    "autoExpand": False,
                                    "maxCharCount": None,
                                }
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        # The import error
        violation = detail[0]
        assert violation.get("type") == "union_tag_invalid"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0]
        assert (
            violation.get("msg")
            == "Input tag 'panel' found using component_discriminator() does not match any of the expected tags: "
            "<FormIoComponentTypeEnum.text_area: 'textarea'>, <FormIoComponentTypeEnum.text_field: 'textfield'>, "
            "<FormIoComponentTypeEnum.radio: 'radio'>, <FormIoComponentTypeEnum.checkbox: 'selectboxes'>, "
            "<FormIoComponentTypeEnum.select: 'select'>, <FormIoComponentTypeEnum.date: 'date'>, <FormIoComponentTypeEnum.time: 'time'>"
        )

    @pytest.mark.anyio
    async def test_update_form_with_conditionals(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "heeft-u-meer-informatie",
                        "eq": "ja",
                    },
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": "textarea",
                            "conditional": {
                                "show": True,
                                "when": "heeft-u-meer-informatie",
                                "eq": "ja",
                            },
                            "input": True,
                            "autoExpand": True,
                            "maxCharCount": 255,
                        },
                    ],
                },
                {
                    "title": "Panel title",
                    "label": "panel-2",
                    "key": "panel-2",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "heeft-u-meer-informatie",
                        "eq": "nee",
                    },
                    "components": [
                        {
                            "label": "Selecteer een optie?",
                            "description": "",
                            "key": "selecteer-een-optie",
                            "type": "selectboxes",
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "heeft-u-meer-informatie",
                                "eq": "nee",
                            },
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
                {
                    "title": "Panel title",
                    "label": "panel-3",
                    "key": "panel-3",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "waarom-meld-u-dit-bij-ons",
                        "eq": "vanwege reden x",
                    },
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.select,
                            "input": True,
                            "widget": "html5",
                            "placeholder": "This is a placeholder value",
                            "conditional": {
                                "show": True,
                                "when": "waarom-meld-u-dit-bij-ons",
                                "eq": "vanwege reden x",
                            },
                            "data": {
                                "values": [
                                    {"label": "label1", "value": "value1"},
                                    {"label": "label2", "value": "value2"},
                                ]
                            },
                        },
                    ],
                },
            ],
        }

        assert form.title != new_data["title"]
        assert form.display != new_data["display"]
        form_components = await form.awaitable_attrs.components
        assert len(form_components) != len(new_data["components"])

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        assert data.get("id") == form.id
        assert data["title"] == new_data["title"]
        assert data["display"] == new_data["display"]
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = await form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_with_conditional_with_none_values(
        self, app: FastAPI, client: AsyncClient, form: Form, auth_user: None
    ) -> None:
        """If no conditional is explicitly set, this is what FormIO sends to the backend"""

        form_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": None,
                        "when": None,
                        "eq": "",
                    },
                    "components": [],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=form_data)

        assert response.status_code == HTTP_200_OK
        body = response.json()

        components = body.get("components")
        assert len(components) == 2

        assert components[1]["conditional"]["when"] is None
        assert components[1]["conditional"]["show"] is None
        assert components[1]["conditional"]["eq"] == ""

    @pytest.mark.anyio
    async def test_update_form_with_conditional_empty_when(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": " ",
                        "eq": "ja",
                    },
                    "components": [],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        body = response.json()
        components = body.get("components")
        assert len(components) == 2

        assert components[1]["conditional"]["when"] == ""
        assert components[1]["conditional"]["show"] is True
        assert components[1]["conditional"]["eq"] == "ja"

    @pytest.mark.anyio
    async def test_update_form_with_conditional_missing_elements(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        # Missing 'show', 'when', 'eq' keys
                    },
                    "components": [],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 3  # Expecting three violations for missing keys

        expected_violations = {
            ("body", "components", 1, "panel", "conditional", "show"): "Field required",
            ("body", "components", 1, "panel", "conditional", "when"): "Field required",
            ("body", "components", 1, "panel", "conditional", "eq"): "Field required",
        }

        for violation in detail:
            loc = tuple(violation.get("loc"))
            assert loc in expected_violations
            assert violation.get("msg") == expected_violations[loc]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "invalid_eq",
        [
            [],
            {},
        ],
    )
    async def test_update_form_conditional_with_invalid_eq_type(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form, invalid_eq: Any
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "heeft-u-meer-informatie",
                        "eq": invalid_eq,
                    },
                    "components": [],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 4

        expected_violations = {
            ("body", "components", 1, "panel", "conditional", "eq", "str"): "Input should be a valid string",
            ("body", "components", 1, "panel", "conditional", "eq", "int"): "Input should be a valid integer",
            ("body", "components", 1, "panel", "conditional", "eq", "float"): "Input should be a valid number",
            ("body", "components", 1, "panel", "conditional", "eq", "bool"): "Input should be a valid boolean",
        }

        for violation in detail:
            loc = tuple(violation.get("loc"))
            assert loc in expected_violations
            assert violation.get("msg") == expected_violations[loc]

    @pytest.mark.anyio
    async def test_update_form_values(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
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
                    "title": "Panel title",
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

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        data = response.json()

        components = await form.awaitable_attrs.components
        await self._assert_components(data.get("components"), components)

    @pytest.mark.anyio
    async def test_update_form_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, form_id=123),
            json={
                "title": "Formulier #1",
                "display": "wizard",
                "classification": 1,
                "components": [],
            },
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_form_with_select(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": FormIoComponentTypeEnum.panel,
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
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=data)

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("id", 0) == form.id
        assert body.get("title") == "Formulier #1"
        assert body.get("display") == "form"

        components = body.get("components")
        assert len(components) == 1

        panel = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == FormIoComponentTypeEnum.panel
        assert panel.get("input") is False

        panel_components = panel.get("components")
        assert len(panel_components) == 1

        select = panel_components[0]
        assert select.get("label") == "Waarom meld u dit bij ons?"
        assert select.get("description") == ""
        assert select.get("key") == "waarom-meld-u-dit-bij-ons"
        assert select.get("type") == FormIoComponentTypeEnum.select
        assert select.get("input") is True
        assert select.get("question") is not None
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
            i = i + 1 @ pytest.mark.anyio

    async def test_update_form_with_time_field(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Hoe laat was dit?",
                            "description": "",
                            "key": "hoe-laat-was-dit",
                            "type": FormIoComponentTypeEnum.time,
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "validate": {
                                "required": True,
                                "required_error_message": "U moet vertellen hoe laat het was!",
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=data)

        assert response.status_code == HTTP_200_OK

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 1

        panel: dict[str, Any] = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Hoe laat was dit?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "hoe-laat-was-dit"
        assert text_field.get("type") == FormIoComponentTypeEnum.time
        assert text_field.get("input")
        assert text_field.get("question") is not None
        assert text_field.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }
        validate = text_field.get("validate")
        assert validate is not None
        assert validate.get("required") is True
        assert validate.get("required_error_message") == "U moet vertellen hoe laat het was!"

    async def test_update_form_with_date_field(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Welke dag was dit?",
                            "description": "",
                            "key": "welke-dag-was-dit",
                            "dayRange": 5,
                            "type": FormIoComponentTypeEnum.date,
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "validate": {
                                "required": True,
                                "required_error_message": "U moet vertellen welke dag het was!",
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=data)

        assert response.status_code == HTTP_200_OK

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 1

        panel: dict[str, Any] = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Welke dag was dit?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "welke-dag-was-dit"
        assert text_field.get("type") == FormIoComponentTypeEnum.date
        assert text_field.get("input")
        assert text_field.get("question") is not None
        assert text_field.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }
        validate = text_field.get("validate")
        assert validate is not None
        assert validate.get("required") is True
        assert validate.get("required_error_message") == "U moet vertellen welke dag het was!"


class TestFormCreate(BaseUnauthorizedTest, BaseFormTest):
    ROUTE_NAME: Final[str] = "form:create"
    METHOD: Final[str] = "POST"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.anyio
    async def test_create_form(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "maxCharCount": 255,
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 2

        first_component: dict[str, Any] = components[0]
        assert first_component.get("label") == "Heeft u meer informatie die u met ons wilt delen?"
        assert first_component.get("description") == "Help tekst bij de vraag."
        assert first_component.get("key") == "heeft-u-meer-informatie"
        assert first_component.get("type") == "textarea"
        assert first_component.get("input")
        assert not first_component.get("autoExpand")
        assert first_component.get("maxCharCount", "") is None
        assert first_component.get("question") is not None
        first_component_validate = first_component.get("validate")
        assert first_component_validate is not None
        assert first_component_validate.get("required") is False

        second_component: dict[str, Any] = components[1]
        assert second_component.get("title") == "Panel title"
        assert second_component.get("label") == "panel-1"
        assert second_component.get("key") == "panel"
        assert second_component.get("type") == "panel"
        assert not second_component.get("input")

        second_child_components: list[dict[str, Any]] = components[1].get("components")

        second_child_component: dict[str, Any] = second_child_components[0]
        assert second_child_component.get("label") == "Waarom meld u dit bij ons?"
        assert second_child_component.get("description") == ""
        assert second_child_component.get("key") == "waarom-meld-u-dit-bij-ons"
        assert second_child_component.get("type") == "textarea"
        assert second_child_component.get("input")
        assert second_child_component.get("autoExpand")
        assert second_child_component.get("maxCharCount") == 255
        assert second_child_component.get("question") is not None
        second_child_component_validate = second_child_component.get("validate")
        assert second_child_component_validate is not None
        assert second_child_component_validate.get("required") is False

    @pytest.mark.anyio
    async def test_create_form_with_jsonlogic(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
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
                    "title": "Panel 2 title",
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
                    "title": "Panel 3 title",
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
                    "title": "Panel 4 title",
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
                    "title": "Panel 5 title",
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

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

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
    async def test_create_form_with_text_field(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.text_field,
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "validate": {
                                "required": True,
                                "required_error_message": "U moet vertellen waarom u dit bij ons meldt!",
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 1

        panel: dict[str, Any] = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Waarom meld u dit bij ons?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "waarom-meld-u-dit-bij-ons"
        assert text_field.get("type") == FormIoComponentTypeEnum.text_field
        assert text_field.get("input")
        assert text_field.get("question") is not None
        assert text_field.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }
        validate = text_field.get("validate")
        assert validate is not None
        assert validate.get("required") is True
        assert validate.get("required_error_message") == "U moet vertellen waarom u dit bij ons meldt!"

    @pytest.mark.anyio
    async def test_create_form_with_select(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel 1 title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": FormIoComponentTypeEnum.panel,
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.select,
                            "input": True,
                            "widget": "html5",
                            "placeholder": "This is a placeholder value",
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "data": {
                                "values": [
                                    {"label": "label1", "value": "value1"},
                                    {"label": "label2", "value": "value2"},
                                ]
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        body = response.json()

        assert body.get("id", 0) > 0
        assert body.get("title") == "Formulier #1"
        assert body.get("display") == "form"

        components = body.get("components")
        assert len(components) == 1

        panel = components[0]
        assert panel.get("title") == "Panel 1 title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == FormIoComponentTypeEnum.panel
        assert panel.get("input") is False
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }

        panel_components = panel.get("components")
        assert len(panel_components) == 1

        select = panel_components[0]
        assert select.get("label") == "Waarom meld u dit bij ons?"
        assert select.get("description") == ""
        assert select.get("key") == "waarom-meld-u-dit-bij-ons"
        assert select.get("type") == FormIoComponentTypeEnum.select
        assert select.get("input") is True
        assert select.get("question") is not None
        assert select.get("widget") == "html5"
        assert select.get("placeholder") == "This is a placeholder value"
        assert select.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }

        select_data = select.get("data")
        assert select_data is not None

        values: list[dict[str, str]] = select_data.get("values", [])
        assert len(values) == 2
        i = 1
        for value in values:
            assert value.get("label") == f"label{i}"
            assert value.get("value") == f"value{i}"
            i = i + 1

    @pytest.mark.anyio
    async def test_create_form_with_conditional_empty_when(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        form_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": " ",
                        "eq": "ja",
                    },
                    "components": [],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=form_data)

        assert response.status_code == HTTP_201_CREATED

        body = response.json()
        components = body.get("components")
        assert len(components) == 2

        assert components[1]["conditional"]["when"] == ""
        assert components[1]["conditional"]["show"] is True
        assert components[1]["conditional"]["eq"] == "ja"

    @pytest.mark.anyio
    async def test_create_form_with_conditional_with_none_values(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        """If no conditional is explicitly set, this is what FormIO sends to the backend"""

        form_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": None,
                        "when": None,
                        "eq": "",
                    },
                    "components": [],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=form_data)

        assert response.status_code == HTTP_201_CREATED
        body = response.json()

        components = body.get("components")
        assert len(components) == 2

        assert components[1]["conditional"]["when"] is None
        assert components[1]["conditional"]["show"] is None
        assert components[1]["conditional"]["eq"] == ""

    @pytest.mark.anyio
    async def test_create_form_with_conditional_missing_elements(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        form_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        # Missing 'show', 'when', 'eq' keys
                    },
                    "components": [],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=form_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 3

        expected_violations = {
            ("body", "components", 1, "panel", "conditional", "show"): "Field required",
            ("body", "components", 1, "panel", "conditional", "when"): "Field required",
            ("body", "components", 1, "panel", "conditional", "eq"): "Field required",
        }

        for violation in detail:
            loc = tuple(violation.get("loc"))
            assert loc in expected_violations
            assert violation.get("msg") == expected_violations[loc]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "invalid_eq",
        [
            [],
            {},
        ],
    )
    async def test_create_form_conditional_with_invalid_eq_type(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form, invalid_eq: Any
    ) -> None:
        form_data = {
            "title": "Formulier #1",
            "display": "wizard",
            "components": [
                {
                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                    "description": "Help tekst bij de vraag.",
                    "key": "heeft-u-meer-informatie",
                    "type": FormIoComponentTypeEnum.text_area,
                    "input": True,
                    "autoExpand": False,
                    "maxCharCount": None,
                },
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "heeft-u-meer-informatie",
                        "eq": invalid_eq,
                    },
                    "components": [],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=form_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 4

        expected_violations = {
            ("body", "components", 1, "panel", "conditional", "eq", "str"): "Input should be a valid string",
            ("body", "components", 1, "panel", "conditional", "eq", "int"): "Input should be a valid integer",
            ("body", "components", 1, "panel", "conditional", "eq", "float"): "Input should be a valid number",
            ("body", "components", 1, "panel", "conditional", "eq", "bool"): "Input should be a valid boolean",
        }

        for violation in detail:
            loc = tuple(violation.get("loc"))
            assert loc in expected_violations
            assert violation.get("msg") == expected_violations[loc]

    @pytest.mark.anyio
    async def test_create_form_with_classification(
        self, app: FastAPI, client: AsyncClient, auth_user: None, classification: Classification
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "classification": classification.id,
            "components": [],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("components") == []
        assert data.get("classification") == classification.id

    @pytest.mark.anyio
    async def test_create_form_with_classification_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "classification": 123456,
            "components": [],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "Classification not found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "title, display, error_type, error_loc, error_msg",
        [
            ("AB", "form", "string_too_short", ["body", "title"], "String should have at least 3 characters"),
            (
                "Valid title",
                "Invalid display",
                "enum",
                ["body", "display"],
                "Input should be 'form', 'wizard' or 'pdf'",
            ),
        ],
    )
    async def test_create_form_violation(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        title: str,
        display: str,
        error_type: str,
        error_loc: list[str],
        error_msg: str,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME), json={"title": title, "display": display, "components": []}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == error_type
        assert violation.get("loc") == error_loc
        assert violation.get("msg") == error_msg

    @pytest.mark.anyio
    async def test_validation_of_classification_id(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME),
            json={"title": "title", "display": "form", "classification": 0, "components": []},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than"
        assert violation.get("loc") == ["body", "classification"]
        assert violation.get("msg") == "Input should be greater than 0"

    @pytest.mark.anyio
    async def test_create_form_invalid_nesting(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "components": [
                        {
                            "label": "Heeft u meer informatie die u met ons wilt delen?",
                            "description": "Help tekst bij de vraag.",
                            "key": "heeft-u-meer-informatie",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": False,
                            "maxCharCount": None,
                            "components": [
                                {
                                    "label": "Waarom meld u dit bij ons?",
                                    "description": "",
                                    "key": "waarom-meld-u-dit-bij-ons",
                                    "type": "textarea",
                                    "input": True,
                                    "autoExpand": True,
                                    "maxCharCount": 255,
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "extra_forbidden"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0, "textarea", "components"]
        assert violation.get("msg") == "Extra inputs are not permitted"
        assert violation.get("input") == [
            {
                "label": "Waarom meld u dit bij ons?",
                "description": "",
                "key": "waarom-meld-u-dit-bij-ons",
                "type": "textarea",
                "input": True,
                "autoExpand": True,
                "maxCharCount": 255,
            },
        ]

    @pytest.mark.anyio
    async def test_create_form_invalid_nesting_panel_with_panel(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
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
                                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                                    "description": "Help tekst bij de vraag.",
                                    "key": "heeft-u-meer-informatie",
                                    "type": "textarea",
                                    "input": True,
                                    "autoExpand": False,
                                    "maxCharCount": None,
                                }
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        # The import error
        violation = detail[0]
        assert violation.get("type") == "union_tag_invalid"
        assert violation.get("loc") == ["body", "components", 0, "panel", "components", 0]
        assert (
            violation.get("msg")
            == "Input tag 'panel' found using component_discriminator() does not match any of the expected tags: "
            "<FormIoComponentTypeEnum.text_area: 'textarea'>, <FormIoComponentTypeEnum.text_field: 'textfield'>, "
            "<FormIoComponentTypeEnum.radio: 'radio'>, <FormIoComponentTypeEnum.checkbox: 'selectboxes'>, "
            "<FormIoComponentTypeEnum.select: 'select'>, <FormIoComponentTypeEnum.date: 'date'>, <FormIoComponentTypeEnum.time: 'time'>"
        )

    @pytest.mark.anyio
    async def test_create_form_with_time_field(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Hoe laat was dit?",
                            "description": "",
                            "key": "hoe-laat-was-dit",
                            "type": FormIoComponentTypeEnum.time,
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "validate": {
                                "required": True,
                                "required_error_message": "U moet vertellen hoe laat het was!",
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 1

        panel: dict[str, Any] = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Hoe laat was dit?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "hoe-laat-was-dit"
        assert text_field.get("type") == FormIoComponentTypeEnum.time
        assert text_field.get("input")
        assert text_field.get("question") is not None
        assert text_field.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }
        validate = text_field.get("validate")
        assert validate is not None
        assert validate.get("required") is True
        assert validate.get("required_error_message") == "U moet vertellen hoe laat het was!"

    @pytest.mark.anyio
    async def test_create_form_with_date_field(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        data = {
            "title": "Formulier #1",
            "display": "form",
            "components": [
                {
                    "title": "Panel title",
                    "label": "panel-1",
                    "key": "panel",
                    "type": "panel",
                    "input": False,
                    "conditional": {
                        "show": True,
                        "when": "somefield",
                        "eq": "somevalue",
                    },
                    "components": [
                        {
                            "label": "Welke dag was dit?",
                            "description": "",
                            "key": "welke-dag-was-dit",
                            "dayRange": 5,
                            "type": FormIoComponentTypeEnum.date,
                            "input": True,
                            "conditional": {
                                "show": True,
                                "when": "otherfield",
                                "eq": "othervalue",
                            },
                            "validate": {
                                "required": True,
                                "required_error_message": "U moet vertellen welke dag het was!",
                            },
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        _id = data.get("id", 0)
        assert isinstance(_id, int)
        assert _id > 0
        assert data.get("title") == "Formulier #1"
        assert data.get("display") == "form"
        assert data.get("classification", "") is None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 1

        panel: dict[str, Any] = components[0]
        assert panel.get("title") == "Panel title"
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert panel.get("conditional") == {
            "show": True,
            "when": "somefield",
            "eq": "somevalue",
        }
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Welke dag was dit?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "welke-dag-was-dit"
        assert text_field.get("type") == FormIoComponentTypeEnum.date
        assert text_field.get("input")
        assert text_field.get("question") is not None
        assert text_field.get("conditional") == {
            "show": True,
            "when": "otherfield",
            "eq": "othervalue",
        }
        validate = text_field.get("validate")
        assert validate is not None
        assert validate.get("required") is True
        assert validate.get("required_error_message") == "U moet vertellen welke dag het was!"


class TestFormClassification:
    ROUTE_NAME: Final[str] = "form:classification"

    @pytest.mark.anyio
    async def test_form_classification_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_form_classification_id_validation(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=0))

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "greater_than_equal"
        assert detail[0].get("loc") == ["path", "classification_id"]
        assert detail[0].get("msg") == "Input should be greater than or equal to 1"

    @pytest.mark.anyio
    async def test_form_classification(self, app: FastAPI, client: AsyncClient, form_with_classification: Form) -> None:
        classification = await form_with_classification.awaitable_attrs.classification
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=classification.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("title") == form_with_classification.title
        assert body.get("display") == form_with_classification.display
        assert len(body.get("components")) == 1
        assert body.get("id") == form_with_classification.id
        assert body.get("created_at") == form_with_classification.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == form_with_classification.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
