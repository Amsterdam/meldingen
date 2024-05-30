from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from meldingen.models import FormIoComponent, StaticForm, StaticFormTypeEnum
from tests.api.v1.endpoints.test_form import BaseFormTest


class BaseStaticFormTest(BaseFormTest):
    async def _assert_component(self, data: dict[str, Any], component: FormIoComponent) -> None:
        await super()._assert_component(data, component)

        # Additional check, a component of a static form should have no question related to it
        assert data.get("question") is None


class TestStaticFormRetrieveByType(BaseStaticFormTest):
    ROUTE_NAME: Final[str] = "static-form:retrieve-by-type"
    METHOD: Final[str] = "GET"

    @pytest.mark.asyncio
    async def test_retrieve_primary_form(self, app: FastAPI, client: AsyncClient, primary_form: StaticForm) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_type=StaticFormTypeEnum.primary))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("type") == primary_form.type
        assert data.get("title") == primary_form.title
        assert data.get("display") == primary_form.display
        assert data.get("created_at") == primary_form.created_at.isoformat()
        assert data.get("updated_at") == primary_form.updated_at.isoformat()

        await self._assert_components(data.get("components"), await primary_form.awaitable_attrs.components)

    @pytest.mark.asyncio
    async def test_retrieve_primary_form_does_not_exists(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, form_type=StaticFormTypeEnum.primary))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"
