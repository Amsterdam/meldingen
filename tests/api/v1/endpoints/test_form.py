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
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import (
    Classification,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoComponentTypeEnum,
    FormIoComponentValue,
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
            else:
                assert isinstance(component, FormIoQuestionComponent)
                await self._assert_component(component_data, component)

    async def _assert_panel_component(self, data: dict[str, Any], component: FormIoPanelComponent) -> None:
        assert data.get("label") == component.label
        assert data.get("key") == component.key
        assert data.get("type") == component.type
        assert data.get("input") == component.input

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

        values_data = data.get("values", [])
        assert isinstance(values_data, list)  # This is here for mypy

        values = await component.awaitable_attrs.values
        if values:
            await self._assert_component_values(values_data, values)

    async def _assert_component(self, data: dict[str, Any], component: FormIoQuestionComponent) -> None:
        assert data.get("label") == component.label
        assert data.get("description") == component.description
        assert data.get("key") == component.key
        assert data.get("type") == component.type
        assert data.get("input") == component.input

        assert data.get("position") == component.position
        assert data.get("question") == component.question_id

        if isinstance(component, FormIoTextAreaComponent):
            assert data.get("autoExpand") == component.auto_expand
            assert data.get("showCharCount") == component.show_char_count


class TestFormList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "form:list"
    METHOD: Final[str] = "GET"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
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
        test_forms: list[Form],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        for form in data:
            assert form.get("classification", "") is None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/10"

    @pytest.mark.asyncio
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
        test_forms: list[Form],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert data[0].get("classification", "") == form_with_classification.classification_id
        for form in data[1:]:
            assert form.get("classification", "") is None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/11"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"title": "Form #1", "display": "form", "id": 1, "classification": None},
                    {"title": "Form #2", "display": "form", "id": 2, "classification": None},
                    {"title": "Form #3", "display": "form", "id": 3, "classification": None},
                    {"title": "Form #4", "display": "form", "id": 4, "classification": None},
                    {"title": "Form #5", "display": "form", "id": 5, "classification": None},
                    {"title": "Form #6", "display": "form", "id": 6, "classification": None},
                    {"title": "Form #7", "display": "form", "id": 7, "classification": None},
                    {"title": "Form #8", "display": "form", "id": 8, "classification": None},
                    {"title": "Form #9", "display": "form", "id": 9, "classification": None},
                    {"title": "Form #10", "display": "form", "id": 10, "classification": None},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"title": "Form #10", "display": "form", "id": 10, "classification": None},
                    {"title": "Form #9", "display": "form", "id": 9, "classification": None},
                    {"title": "Form #8", "display": "form", "id": 8, "classification": None},
                    {"title": "Form #7", "display": "form", "id": 7, "classification": None},
                    {"title": "Form #6", "display": "form", "id": 6, "classification": None},
                    {"title": "Form #5", "display": "form", "id": 5, "classification": None},
                    {"title": "Form #4", "display": "form", "id": 4, "classification": None},
                    {"title": "Form #3", "display": "form", "id": 3, "classification": None},
                    {"title": "Form #2", "display": "form", "id": 2, "classification": None},
                    {"title": "Form #1", "display": "form", "id": 1, "classification": None},
                ],
            ),
            (
                "title",
                SortingDirection.ASC,
                [
                    {"title": "Form #1", "display": "form", "id": 1, "classification": None},
                    {"title": "Form #10", "display": "form", "id": 10, "classification": None},
                    {"title": "Form #2", "display": "form", "id": 2, "classification": None},
                    {"title": "Form #3", "display": "form", "id": 3, "classification": None},
                    {"title": "Form #4", "display": "form", "id": 4, "classification": None},
                    {"title": "Form #5", "display": "form", "id": 5, "classification": None},
                    {"title": "Form #6", "display": "form", "id": 6, "classification": None},
                    {"title": "Form #7", "display": "form", "id": 7, "classification": None},
                    {"title": "Form #8", "display": "form", "id": 8, "classification": None},
                    {"title": "Form #9", "display": "form", "id": 9, "classification": None},
                ],
            ),
            (
                "title",
                SortingDirection.DESC,
                [
                    {"title": "Form #9", "display": "form", "id": 9, "classification": None},
                    {"title": "Form #8", "display": "form", "id": 8, "classification": None},
                    {"title": "Form #7", "display": "form", "id": 7, "classification": None},
                    {"title": "Form #6", "display": "form", "id": 6, "classification": None},
                    {"title": "Form #5", "display": "form", "id": 5, "classification": None},
                    {"title": "Form #4", "display": "form", "id": 4, "classification": None},
                    {"title": "Form #3", "display": "form", "id": 3, "classification": None},
                    {"title": "Form #2", "display": "form", "id": 2, "classification": None},
                    {"title": "Form #10", "display": "form", "id": 10, "classification": None},
                    {"title": "Form #1", "display": "form", "id": 1, "classification": None},
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
        test_forms: list[Form],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["title"] == expected[i]["title"]
            assert data[i]["display"] == expected[i]["display"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "form 0-49/10"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "title",
                SortingDirection.DESC,
                [
                    {"title": "Form #7", "display": "form", "id": 7, "classification": None},
                    {"title": "Form #6", "display": "form", "id": 6, "classification": None},
                ],
            ),
            (
                3,
                1,
                "title",
                SortingDirection.ASC,
                [
                    {"title": "Form #10", "display": "form", "id": 10, "classification": None},
                    {"title": "Form #2", "display": "form", "id": 2, "classification": None},
                    {"title": "Form #3", "display": "form", "id": 3, "classification": None},
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
        test_forms: list[Form],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["id"] == expected[i]["id"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["title"] == expected[i]["title"]
            assert data[i]["display"] == expected[i]["display"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/10"


class TestFormRetrieve(BaseFormTest):
    ROUTE_NAME: Final[str] = "form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.asyncio
    async def test_retrieve_form(self, app: FastAPI, client: AsyncClient, form: Form) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form.id
        assert data.get("title") == form.title
        assert data.get("display") == form.display
        assert data.get("created_at") == form.created_at.isoformat()
        assert data.get("updated_at") == form.updated_at.isoformat()

        await self._assert_components(data.get("components"), await form.awaitable_attrs.components)

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_retrieve_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "form_title",
        [("Form #1",), ("Form #2",)],
        indirect=True,
    )
    async def test_delete_form(self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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
                    "showCharCount": False,
                },
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
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "showCharCount": True,
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

    @pytest.mark.asyncio
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
                    "showCharCount": True,
                },
                {
                    "label": "Waarom meld u dit bij ons?",
                    "description": "",
                    "key": "waarom-meld-u-dit-bij-ons",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
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

    @pytest.mark.asyncio
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
                    "showCharCount": True,
                },
                {
                    "label": "Waarom meld u dit bij ons?",
                    "description": "",
                    "key": "waarom-meld-u-dit-bij-ons",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_update_form_assign_classification_that_is_already_assigned_to_another_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: Form,
        form_with_classification: Form,
    ) -> None:
        new_data = {
            "title": "Form",
            "display": "form",
            "classification": 1,
            "components": [
                {
                    "label": "Wat is uw klacht?",
                    "description": "",
                    "key": "wat-is-uw_klacht",
                    "type": "textarea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                }
            ],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification") == 1

    @pytest.mark.asyncio
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

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than"
        assert violation.get("loc") == ["body", "classification"]
        assert violation.get("msg") == "Input should be greater than 0"

    @pytest.mark.asyncio
    async def test_update_form_invalid_nesting_panel_with_panel(
        self, app: FastAPI, client: AsyncClient, auth_user: None, form: Form
    ) -> None:
        new_data = {
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
                                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                                    "description": "Help tekst bij de vraag.",
                                    "key": "heeft-u-meer-informatie",
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

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=form.id), json=new_data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

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
            "<FormIoComponentTypeEnum.select: 'select'>"
        )

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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


class TestFormCreate(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "form:create"
    METHOD: Final[str] = "POST"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    @pytest.mark.asyncio
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
                    "showCharCount": False,
                },
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
                            "type": "textarea",
                            "input": True,
                            "autoExpand": True,
                            "showCharCount": True,
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id", 0) == 1
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
        assert not first_component.get("showCharCount")
        assert first_component.get("question") is not None

        second_component: dict[str, Any] = components[1]
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
        assert second_child_component.get("showCharCount")
        assert second_child_component.get("question") is not None

    @pytest.mark.asyncio
    async def test_create_form_with_text_field(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
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
                            "label": "Waarom meld u dit bij ons?",
                            "description": "",
                            "key": "waarom-meld-u-dit-bij-ons",
                            "type": FormIoComponentTypeEnum.text_field,
                            "input": True,
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id", 0) == 1
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
        assert panel.get("label") == "panel-1"
        assert panel.get("key") == "panel"
        assert panel.get("type") == "panel"
        assert not panel.get("input")

        panel_components: list[dict[str, Any]] = components[0].get("components")

        text_field: dict[str, Any] = panel_components[0]
        assert text_field.get("label") == "Waarom meld u dit bij ons?"
        assert text_field.get("description") == ""
        assert text_field.get("key") == "waarom-meld-u-dit-bij-ons"
        assert text_field.get("type") == FormIoComponentTypeEnum.text_field
        assert text_field.get("input")
        assert text_field.get("question") is not None

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == error_type
        assert violation.get("loc") == error_loc
        assert violation.get("msg") == error_msg

    @pytest.mark.asyncio
    async def test_validation_of_classification_id(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME),
            json={"title": "title", "display": "form", "classification": 0, "components": []},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "greater_than"
        assert violation.get("loc") == ["body", "classification"]
        assert violation.get("msg") == "Input should be greater than 0"

    @pytest.mark.asyncio
    async def test_create_form_invalid_nesting(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
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
                            "label": "Heeft u meer informatie die u met ons wilt delen?",
                            "description": "Help tekst bij de vraag.",
                            "key": "heeft-u-meer-informatie",
                            "type": "textarea",
                            "input": True,
                            "autoExpand": False,
                            "showCharCount": False,
                            "components": [
                                {
                                    "label": "Waarom meld u dit bij ons?",
                                    "description": "",
                                    "key": "waarom-meld-u-dit-bij-ons",
                                    "type": "textarea",
                                    "input": True,
                                    "autoExpand": True,
                                    "showCharCount": True,
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

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
                "showCharCount": True,
            },
        ]

    @pytest.mark.asyncio
    async def test_create_form_invalid_nesting_panel_with_panel(
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
                                    "label": "Heeft u meer informatie die u met ons wilt delen?",
                                    "description": "Help tekst bij de vraag.",
                                    "key": "heeft-u-meer-informatie",
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

        response = await client.post(app.url_path_for(self.ROUTE_NAME), json=data)

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

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
            "<FormIoComponentTypeEnum.select: 'select'>"
        )


class TestFormClassification:
    ROUTE_NAME: Final[str] = "form:classification"

    @pytest.mark.asyncio
    async def test_form_classification_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_form_classification_id_validation(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=0))

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "greater_than_equal"
        assert detail[0].get("loc") == ["path", "classification_id"]
        assert detail[0].get("msg") == "Input should be greater than or equal to 1"

    @pytest.mark.asyncio
    async def test_form_classification(self, app: FastAPI, client: AsyncClient, form_with_classification: Form) -> None:
        classification = await form_with_classification.awaitable_attrs.classification
        response = await client.get(app.url_path_for(self.ROUTE_NAME, classification_id=classification.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("title") == form_with_classification.title
        assert body.get("display") == form_with_classification.display
        assert len(body.get("components")) == 1
        assert body.get("id") == form_with_classification.id
        assert body.get("created_at") == form_with_classification.created_at.isoformat()
        assert body.get("updated_at") == form_with_classification.updated_at.isoformat()
