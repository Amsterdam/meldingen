from abc import ABCMeta, abstractmethod
from os import path
from typing import Any, Final, override
from uuid import uuid4

import pytest
from azure.storage.blob.aio import ContainerClient
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from meldingen_core.malware import BaseMalwareScanner
from meldingen_core.statemachine import MeldingStates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from meldingen.models import Attachment, Classification, Form, Melding, Question
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestMeldingCreate:
    ROUTE_NAME_CREATE: Final[str] = "melding:create"

    @pytest.mark.anyio
    async def test_create_melding(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") == 1
        assert data.get("text") == "This is a test melding."
        assert data.get("state") == MeldingStates.NEW
        assert data.get("classification", "") is None
        assert data.get("token") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.anyio
    @pytest.mark.parametrize("classification_name,", ["classification_name"], indirect=True)
    async def test_create_melding_with_classification(
        self, app: FastAPI, client: AsyncClient, classification: Classification
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "classification_name"})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") is not None
        assert data.get("text") == "classification_name"
        assert data.get("state") == MeldingStates.CLASSIFIED
        assert data.get("classification") == classification.id

    @pytest.mark.anyio
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


class TestMeldingList(BaseUnauthorizedTest, BasePaginationParamsTest, BaseSortParamsTest):
    ROUTE_NAME: Final[str] = "melding:list"
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
    async def test_list_meldingen_paginated(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        expected_result: int,
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"limit": limit, "offset": offset})

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data) == expected_result
        assert response.headers.get("content-range") == f"melding {offset}-{limit - 1 + offset}/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "attribute, direction, expected",
        [
            (
                "id",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                ],
            ),
            (
                "id",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                ],
            ),
            (
                "text",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                ],
            ),
            (
                "text",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 9", "state": "new", "classification": None},
                    {"text": "This is a test melding. 8", "state": "new", "classification": None},
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                    {"text": "This is a test melding. 5", "state": "new", "classification": None},
                    {"text": "This is a test melding. 4", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 0", "state": "new", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_meldingen_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"sort": f'["{attribute}", "{direction}"]'}
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["text"] == expected[i]["text"]
            assert data[i]["state"] == expected[i]["state"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == "melding 0-49/10"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "limit, offset, attribute, direction, expected",
        [
            (
                2,
                2,
                "text",
                SortingDirection.DESC,
                [
                    {"text": "This is a test melding. 7", "state": "new", "classification": None},
                    {"text": "This is a test melding. 6", "state": "new", "classification": None},
                ],
            ),
            (
                3,
                1,
                "text",
                SortingDirection.ASC,
                [
                    {"text": "This is a test melding. 1", "state": "new", "classification": None},
                    {"text": "This is a test melding. 2", "state": "new", "classification": None},
                    {"text": "This is a test melding. 3", "state": "new", "classification": None},
                ],
            ),
        ],
    )
    async def test_list_meldingen_paginated_and_sorted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        limit: int,
        offset: int,
        attribute: str,
        direction: SortingDirection,
        expected: list[dict[str, Any]],
        meldingen: list[Melding],
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME),
            params={"limit": limit, "offset": offset, "sort": f'["{attribute}", "{direction}"]'},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()

        for i in range(len(expected)):
            assert data[i]["text"] == expected[i]["text"]
            assert data[i]["state"] == expected[i]["state"]
            assert data[i]["classification"] == expected[i]["classification"]
            assert data[i]["created_at"] is not None
            assert data[i]["updated_at"] is not None

        assert response.headers.get("content-range") == f"melding {offset}-{limit - 1 + offset}/10"


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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_text", ["Er ligt poep op de stoep.", "Er is een matras naast de prullenbak gedumpt."], indirect=True
    )
    async def test_retrieve_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=melding.id))

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data.get("id") == melding.id
        assert data.get("text") == melding.text
        assert data.get("state") == MeldingStates.NEW
        assert data.get("classification", "") is None
        assert data.get("created_at") == melding.created_at.isoformat()
        assert data.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_retrieve_melding_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=1))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Not Found"


class BaseTokenAuthenticationTest(metaclass=ABCMeta):
    @abstractmethod
    def get_route_name(self) -> str: ...

    @abstractmethod
    def get_method(self) -> str: ...

    def get_json(self) -> dict[str, Any] | None:
        return None

    @pytest.mark.anyio
    async def test_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            json=self.get_json(),
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_token_invalid(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": ""},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_token_expired(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestMeldingUpdate(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:update"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "PATCH"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"text": "classification_name"}

    @pytest.mark.anyio
    async def test_update_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), params={"token": ""}, json=self.get_json()
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_update_melding_classification_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "classification_name")],
        indirect=True,
    )
    async def test_update_melding(
        self, app: FastAPI, client: AsyncClient, melding: Melding, classification: Classification
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == "classification_name"
        assert body.get("state") == MeldingStates.CLASSIFIED
        assert body.get("classification") == classification.id
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()


class TestMeldingAnswerQuestions(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:answer_questions"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken")],
        indirect=True,
    )
    async def test_answer_questions(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_answer_questions_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.PROCESSING, "supersecrettoken")],
        indirect=True,
    )
    async def test_answer_questions_wrong_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingAddAttachments(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-attachments"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.QUESTIONS_ANSWERED, "supersecrettoken")],
        indirect=True,
    )
    async def test_add_attachments(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.ATTACHMENTS_ADDED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_add_attachments_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=1), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.PROCESSING, "supersecrettoken")],
        indirect=True,
    )
    async def test_add_attachments_wrong_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingSubmitLocation:
    def get_route_name(self) -> str:
        return "melding:submit-location"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_geo_location"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                "POINT(52.3680 4.8970)",
            )
        ],
        indirect=True,
    )
    async def test_submit_location(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.LOCATION_SUBMITTED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.ATTACHMENTS_ADDED, "supersecrettoken")],
        indirect=True,
    )
    async def test_submit_location_no_location_added(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Location must be added before submitting"}

    @pytest.mark.anyio
    async def test_submit_location_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_submit_location_token_invalid(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("De restafvalcontainer is vol.", MeldingStates.ATTACHMENTS_ADDED, "supersecrettoken", "PT1H")],
        indirect=True,
    )
    async def test_submit_location_token_expired(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED


class TestMeldingProcess(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:process"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_process_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.PROCESSING
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_process_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_process_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.PROCESSING)], indirect=True
    )
    async def test_complete_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.COMPLETED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_text", ["Er ligt poep op de stoep."], indirect=True)
    async def test_complete_melding_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(self.get_method(), app.url_path_for(self.get_route_name(), melding_id=404))

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()

        assert body.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.COMPLETED)], indirect=True
    )
    async def test_complete_melding_wrong_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingQuestionAnswer:
    ROUTE_NAME_CREATE: Final[str] = "melding:answer-question"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"==":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"==":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question_without_component(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
        db_session: AsyncSession,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        await db_session.delete(panel_components[0])
        await db_session.commit()

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "jsonlogic"],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"!=":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
            )
        ],
        indirect=[
            "classification_name",
            "jsonlogic",
        ],
    )
    async def test_answer_question_invalid_input(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
        body = response.json()
        detail = body.get("detail")
        assert detail == "Invalid input"

    @pytest.mark.anyio
    async def test_answer_question_melding_does_not_exists(
        self,
        app: FastAPI,
        client: AsyncClient,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=999, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"

    @pytest.mark.anyio
    async def test_answer_question_unauthorized_token_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    async def test_answer_question_token_missing(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            json=data,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_answer_question_melding_not_classified(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        form_with_classification: Form,
    ) -> None:
        components = await form_with_classification.awaitable_attrs.components
        assert len(components) == 1

        panel = components[0]
        panel_components = await panel.awaitable_attrs.components
        assert len(panel_components) == 1

        question = await panel_components[0].awaitable_attrs.question
        assert isinstance(question, Question)

        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=question.id),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "Melding not classified"

    @pytest.mark.anyio
    async def test_answer_question_does_not_exists(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
    ) -> None:
        data = {"text": "dit is het antwoord op de vraag"}

        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id, question_id=999),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "test_classification")],
        indirect=[
            "classification_name",
        ],
    )
    async def test_answer_question_not_connected_to_form(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        db_session: AsyncSession,
    ) -> None:
        question = Question(text="is dit een vraag?")
        db_session.add(question)
        await db_session.commit()

        data = {"text": "Ja, dit is een vraag"}

        response = await client.post(
            app.url_path_for(
                self.ROUTE_NAME_CREATE, melding_id=melding_with_classification.id, question_id=question.id
            ),
            params={"token": "supersecuretoken"},
            json=data,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        data = response.json()
        assert data.get("detail") == "Not Found"


async def assert_container_empty(container_client: ContainerClient) -> None:
    count = 0
    async for _ in container_client.list_blob_names():
        count += 1

    assert count == 0


class TestMeldingUploadAttachment:
    ROUTE_NAME_CREATE: Final[str] = "melding:attachment"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "filename"],
        [
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.jpg"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.png"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.webp"),
        ],
    )
    async def test_upload_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
        malware_scanner_override: BaseMalwareScanner,
        filename: str,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        filename,
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_200_OK

        await db_session.refresh(melding)
        attachments = await melding.awaitable_attrs.attachments
        assert len(attachments) == 1

        await db_session.refresh(attachments[0])

        assert attachments[0].original_filename == filename

        split_path, _ = attachments[0].file_path.rsplit(".", 1)
        optimized_path = f"{split_path}-optimized.webp"
        assert attachments[0].optimized_path == optimized_path

        thumbnail_path = f"{split_path}-thumbnail.webp"
        assert attachments[0].thumbnail_path == thumbnail_path

        blob_client = container_client.get_blob_client(attachments[0].file_path)
        async with blob_client:
            assert await blob_client.exists() is True
            properties = await blob_client.get_blob_properties()

        assert properties.size == path.getsize(
            path.join(
                path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                "resources",
                filename,
            )
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_too_large(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "too-large.jpg",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert response.json().get("detail") == "Allowed content size exceeded"
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "filename"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "test_file.txt")],
    )
    async def test_upload_attachment_media_type_not_allowed(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        filename: str,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        filename,
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        body = response.json()
        assert body.get("detail") == "Attachment not allowed"
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_media_type_integrity_validation_fails(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
            files={
                "file": (
                    "amsterdam-logo.png",
                    open(
                        path.join(
                            path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                            "resources",
                            "amsterdam-logo.png",
                        ),
                        "rb",
                    ),
                    "image/jpeg",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        body = response.json()
        assert body.get("detail") == "Media type of data does not match provided media type"
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    async def test_upload_attachment_melding_not_found(
        self, app: FastAPI, client: AsyncClient, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=123),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_token_missing(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    async def test_upload_attachment_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED
        await assert_container_empty(container_client)

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_upload_attachment_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding, container_client: ContainerClient
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            files={
                "file": open(
                    path.join(
                        path.abspath(path.dirname(path.dirname(path.dirname(path.dirname(__file__))))),
                        "resources",
                        "test_file.txt",
                    ),
                    "rb",
                ),
            },
            # We have to provide the header and boundary manually, otherwise httpx will set the content-type
            # to application/json and the request will fail.
            headers={"Content-Type": "multipart/form-data; boundary=----MeldingenAttachmentFileUpload"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED
        await assert_container_empty(container_client)


class TestMeldingDownloadAttachment:
    ROUTE_NAME: Final[str] = "melding:attachment-download"

    @pytest.mark.anyio
    async def test_download_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_download_attachment_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")

        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_download_attachment_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_download_attachment_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_download_attachment_attached_to_other_melding(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, db_session: AsyncSession
    ) -> None:
        melding = Melding(text="Hoi!", token="supersecuretoken")

        db_session.add(melding)
        await db_session.commit()

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_attachment(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, container_client: ContainerClient
    ) -> None:
        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_optimized_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "optimized"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_optimized_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        db_session: AsyncSession,
    ) -> None:
        attachment.optimized_path = f"/tmp/{uuid4()}/optimized.webp"
        db_session.add(attachment)
        await db_session.commit()

        blob_client = container_client.get_blob_client(attachment.optimized_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "optimized"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_thumbnail_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "thumbnail"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_download_thumbnail_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        db_session: AsyncSession,
    ) -> None:
        attachment.thumbnail_path = f"/tmp/{uuid4()}/thumbnail.webp"
        db_session.add(attachment)
        await db_session.commit()

        blob_client = container_client.get_blob_client(attachment.thumbnail_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken", "type": "thumbnail"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"


class TestMeldingListAttachments:
    ROUTE_NAME: Final[str] = "melding:attachments"

    @pytest.mark.anyio
    async def test_list_attachments_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_list_attachments_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token", "melding_token_expires"], [("supersecuretoken", "PT1H")], indirect=True)
    async def test_list_attachments_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecuretoken",)])
    async def test_list_attachments(self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK

        attachments = await melding_with_attachments.awaitable_attrs.attachments
        body = response.json()

        assert len(attachments) == len(body)


class TestMeldingDeleteAttachmentAction:
    ROUTE_NAME: Final[str] = "melding:attachment-delete"

    @pytest.mark.anyio
    async def test_delete_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_delete_attachment_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")

        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_delete_attachment_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_delete_attachment_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_delete_attachment_attached_to_other_melding(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, db_session: AsyncSession
    ) -> None:
        melding = Melding(text="Hoi!", token="supersecuretoken")

        db_session.add(melding)
        await db_session.commit()

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment
    ) -> None:
        melding = await attachment.awaitable_attrs.melding

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_delete_attachment(
        self, app: FastAPI, client: AsyncClient, attachment: Attachment, container_client: ContainerClient
    ) -> None:
        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK

        async with blob_client:
            assert await blob_client.exists() == False


class TestAddLocationToMeldingAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:location-add"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "POST"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [52.3680605, 4.897092]},
            "properties": {},
        }

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
        indirect=True,
    )
    async def test_add_location_to_melding(
        self, app: FastAPI, client: AsyncClient, melding: Melding, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json=geojson,
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("geo_location").get("type") == geojson["type"]
        assert body.get("geo_location").get("geometry").get("type") == geojson["geometry"]["type"]
        assert body.get("geo_location").get("geometry").get("coordinates") == geojson["geometry"]["coordinates"]

    @pytest.mark.anyio
    async def test_add_location_to_melding_melding_not_found(
        self, app: FastAPI, client: AsyncClient, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=123),
            params={"token": "test"},
            json=geojson,
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "geojson_geometry"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                {
                    "type": "Polygon",
                    "coordinates": [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]]],
                },
            )
        ],
        indirect=True,
    )
    async def test_add_location_wrong_geometry_type(
        self, app: FastAPI, client: AsyncClient, melding: Melding, geojson: dict[str, Any]
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecrettoken"},
            json=geojson,
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")

        assert len(detail) == 6
        assert detail[0].get("msg") == "Input should be 'Point'"


class TestMeldingAddContactAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:contact-add"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "POST"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"email": "user@example.com", "phone": "+31612345678"}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "email", "phone"],
        [
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "melder@example.com", "+31612345678"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", None, "+31612345678"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "melder@example.com", None),
        ],
    )
    async def test_add_contact(
        self, app: FastAPI, client: AsyncClient, melding: Melding, email: str | None, phone: str | None
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json={"email": email, "phone": phone},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data.get("email") == email
        assert data.get("phone") == phone

    @pytest.mark.anyio
    async def test_add_contact_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME, melding_id=999),
            params={"token": "nonexistingtoken"},
            json={"email": "user@example.com", "phone": "+31612345678"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestMeldingContactInfoAdded:
    def get_route_name(self) -> str:
        return "melding:add-contact-info"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_email", "melding_phone"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "supersecrettoken",
                None,
                None,
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "supersecrettoken",
                "melder@example.com",
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "supersecrettoken",
                None,
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "supersecrettoken",
                "melder@example.com",
                None,
            ),
        ],
        indirect=True,
    )
    async def test_contact_info_added(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.CONTACT_INFO_ADDED
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()

    @pytest.mark.anyio
    async def test_contact_info_added_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_contact_info_added_token_invalid(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED
