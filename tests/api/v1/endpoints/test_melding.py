import os
import shutil
from os import path
from typing import Any, Final

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core import SortingDirection
from meldingen_core.statemachine import MeldingStates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
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


class TestMeldingUpdate:
    ROUTE_NAME: Final[str] = "melding:update"

    @pytest.mark.anyio
    async def test_update_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), json={"text": "classification_name"}
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()

        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("type") == "missing"
        assert detail[0].get("loc") == ["query", "token"]
        assert detail[0].get("msg") == "Field required"

    @pytest.mark.anyio
    async def test_update_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=1), params={"token": ""}, json={"text": "classification_name"}
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_melding_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": ""},
            json={"text": "classification_name"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_update_melding_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": "supersecuretoken"},
            json={"text": "classification_name"},
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

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
            json={"text": "classification_name"},
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
            json={"text": "classification_name"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == "classification_name"
        assert body.get("state") == MeldingStates.CLASSIFIED
        assert body.get("classification") == classification.id
        assert body.get("created_at") == melding.created_at.isoformat()
        assert body.get("updated_at") == melding.updated_at.isoformat()


class TestMeldingAnswerQuestions:
    ROUTE_NAME: Final[str] = "melding:answer_questions"

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
    async def test_answer_questions_token_invalid(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "PT1H")],
        indirect=True,
    )
    async def test_answer_questions_token_expired(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_401_UNAUTHORIZED

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


class TestMeldingUploadAttachment:
    ROUTE_NAME_CREATE: Final[str] = "melding:attachment"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment(
        self, app: FastAPI, client: AsyncClient, melding: Melding, db_session: AsyncSession
    ) -> None:
        response = await client.post(
            app.url_path_for(self.ROUTE_NAME_CREATE, melding_id=melding.id),
            params={"token": melding.token},
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

        assert response.status_code == HTTP_200_OK

        await db_session.refresh(melding)
        attachments = await melding.awaitable_attrs.attachments
        assert len(attachments) == 1

        assert path.exists(attachments[0].file_path)

        os.remove(attachments[0].file_path)

    @pytest.mark.anyio
    async def test_upload_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_token_missing(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
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

    @pytest.mark.anyio
    async def test_upload_attachment_unauthorized_token_invalid(
        self, app: FastAPI, client: AsyncClient, melding: Melding
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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_token_expires"],
        [("nice text", MeldingStates.CLASSIFIED, "supersecuretoken", "PT1H")],
        indirect=True,
    )
    async def test_upload_attachment_unauthorized_token_expired(
        self, app: FastAPI, client: AsyncClient, melding: Melding
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
    async def test_download_attachment(self, app: FastAPI, client: AsyncClient, attachment: Attachment) -> None:
        os.makedirs(path.dirname(attachment.file_path))
        with open(attachment.file_path, "wb") as file:
            file.write(b"some data")

        melding = await attachment.awaitable_attrs.melding

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id, attachment_id=attachment.id),
            params={"token": "supersecuretoken"},
        )

        shutil.rmtree(path.dirname(attachment.file_path))

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
