from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Classification, FormIoForm
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseUnauthorizedTest


class TestFormList(BaseUnauthorizedTest, BasePaginationParamsTest):
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
    async def test_list_forms(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        test_forms: list[FormIoForm],
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
        form_with_classification: FormIoForm,
        limit: int,
        offset: int,
        expected_result: int,
        test_forms: list[FormIoForm],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert data[0].get("classification", "") == form_with_classification.classification_id
        for form in data[1:]:
            assert form.get("classification", "") is None

        assert response.headers.get("content-range") == f"form {offset}-{limit - 1 + offset}/11"


class TestFormRetrieve:
    ROUTE_NAME: Final[str] = "form:retrieve"
    METHOD: Final[str] = "GET"

    @pytest.mark.asyncio
    async def test_retrieve_form(self, app: FastAPI, client: AsyncClient, form: FormIoForm) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == form.id
        assert data.get("title") == form.title
        assert data.get("display") == form.display
        assert len(data.get("components")) == len(await form.awaitable_attrs.components)

    @pytest.mark.asyncio
    async def test_retrieve_form_with_classification(
        self, app: FastAPI, client: AsyncClient, form_with_classification: FormIoForm
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
    async def test_delete_form(self, app: FastAPI, client: AsyncClient, auth_user: None, form: FormIoForm) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=form.id))

        assert response.status_code == HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_form_that_does_not_exist(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    async def test_unable_to_delete_primary_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, primary_form: FormIoForm
    ) -> None:
        response = await client.delete(app.url_path_for(self.ROUTE_NAME, form_id=primary_form.id))

        assert response.status_code == HTTP_404_NOT_FOUND


class TestFormUpdate(BaseUnauthorizedTest):
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
        form: FormIoForm,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "components": [
                {
                    "label": "extra-vraag1",
                    "description": "Heeft u meer informatie die u met ons wilt delen?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "extra-vraag2",
                    "description": "Waarom meld u dit bij ons?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
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
        assert len(data["components"]) == len(new_data["components"])
        assert data.get("classification", "") is None

    @pytest.mark.asyncio
    async def test_update_form_with_new_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: FormIoForm,
        classification: Classification,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "classification": classification.id,
            "components": [
                {
                    "label": "extra-vraag1",
                    "description": "Heeft u meer informatie die u met ons wilt delen?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "extra-vraag2",
                    "description": "Waarom meld u dit bij ons?",
                    "key": "textArea",
                    "type": "textArea",
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
        assert isinstance(new_data["components"], list)  # This is here for mypy
        assert len(data["components"]) == len(new_data["components"])
        assert data.get("classification", "") == classification.id

    @pytest.mark.asyncio
    async def test_update_form_change_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form_with_classification: FormIoForm,
        classification: Classification,
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "classification": classification.id,
            "components": [
                {
                    "label": "extra-vraag1",
                    "description": "Heeft u meer informatie die u met ons wilt delen?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
                },
                {
                    "label": "extra-vraag2",
                    "description": "Waarom meld u dit bij ons?",
                    "key": "textArea",
                    "type": "textArea",
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
        assert isinstance(new_data["components"], list)  # This is here for mypy
        assert len(data["components"]) == len(new_data["components"])
        assert data.get("classification", "") == classification.id

    @pytest.mark.asyncio
    async def test_update_form_with_classification_that_does_not_exist(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: FormIoForm,
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
        form_with_classification: FormIoForm,
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
    async def test_update_form_classification_id_validation(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        form: FormIoForm,
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
    async def test_unable_to_update_primary_form(
        self, app: FastAPI, client: AsyncClient, auth_user: None, primary_form: FormIoForm
    ) -> None:
        new_data = {
            "title": "Formulier #1",
            "display": "pdf",
            "components": [],
        }

        response = await client.put(app.url_path_for(self.ROUTE_NAME, form_id=primary_form.id), json=new_data)

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
                    "label": "extra-vraag-1",
                    "description": "Heeft u meer informatie die u met ons wilt delen?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": False,
                    "showCharCount": False,
                },
                {
                    "label": "extra-vraag-2",
                    "description": "Waarom meld u dit bij ons?",
                    "key": "textArea",
                    "type": "textArea",
                    "input": True,
                    "autoExpand": True,
                    "showCharCount": True,
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

        components = data.get("components")
        assert isinstance(components, list)
        assert components is not None
        assert len(components) == 2

        first_component: dict[str, Any] = components[0]
        assert first_component.get("label") == "extra-vraag-1"
        assert first_component.get("description") == "Heeft u meer informatie die u met ons wilt delen?"
        assert first_component.get("key") == "textArea"
        assert first_component.get("type") == "textArea"
        assert first_component.get("input") == True
        assert first_component.get("autoExpand") == False
        assert first_component.get("showCharCount") == False

        second_component: dict[str, Any] = components[1]
        assert second_component.get("label") == "extra-vraag-2"
        assert second_component.get("description") == "Waarom meld u dit bij ons?"
        assert second_component.get("key") == "textArea"
        assert second_component.get("type") == "textArea"
        assert second_component.get("input") == True
        assert second_component.get("autoExpand") == True
        assert second_component.get("showCharCount") == True

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
