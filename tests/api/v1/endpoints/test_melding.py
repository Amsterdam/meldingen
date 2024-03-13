from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core.statemachine import MeldingStates
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Melding
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseUnauthorizedTest


class TestMeldingCreate:
    ROUTE_NAME_CREATE: Final[str] = "melding:create"

    @pytest.mark.asyncio
    async def test_create_melding(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("text") == "This is a test melding."
        assert data.get("state") == MeldingStates.NEW

    @pytest.mark.asyncio
    async def test_create_melding_text_minimum_length_violation(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": ""})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        detail = data.get("detail")
        assert len(detail) == 1

        violation = detail[0]
        assert violation.get("type") == "string_too_short"
        assert violation.get("loc") == ["body", "text"]
        assert violation.get("msg") == "String should have at least 1 character"


class TestMeldingList(BaseUnauthorizedTest, BasePaginationParamsTest):
    ROUTE_NAME: Final[str] = "melding:list"
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
    async def test_list_meldingen(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        test_meldingen: list[Melding],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result


class TestMeldingRetrieve(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "melding:retrieve"
    METHOD: Final[str] = "GET"
    PATH_PARAMS: dict[str, Any] = {"melding_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return self.METHOD

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "melding_text", ["Er ligt poep op de stoep.", "Er is een matras naast de prullenbak gedumpt."], indirect=True
    )
    async def test_retrieve_melding(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=test_melding.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == test_melding.id
        assert data.get("text") == test_melding.text
        assert data.get("state") == MeldingStates.NEW

    @pytest.mark.asyncio
    async def test_retrieve_melding_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class TestMeldingProcess(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:process"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_process_melding(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.PROCESSING

    @pytest.mark.asyncio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_process_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_process_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingComplete(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:complete"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.PROCESSING)], indirect=True)
    async def test_complete_melding(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.COMPLETED

    @pytest.mark.asyncio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_complete_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_complete_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, test_melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), **self.get_path_params())
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"
