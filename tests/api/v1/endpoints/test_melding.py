from abc import ABCMeta, abstractmethod
from os import path
from typing import Any, Final, override
from uuid import uuid4

import pytest
from azure.storage.blob.aio import ContainerClient
from fastapi import FastAPI
from httpx import AsyncClient
from mailpit.client.api import API
from meldingen_core import SortingDirection
from meldingen_core.malware import BaseMalwareScanner
from meldingen_core.statemachine import MeldingStates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from meldingen.models import Answer, Asset, AssetType, Attachment, Classification, Form, Melding, Question
from tests.api.v1.endpoints.base import BasePaginationParamsTest, BaseSortParamsTest, BaseUnauthorizedTest


class TestMeldingCreate:
    ROUTE_NAME_CREATE: Final[str] = "melding:create"

    @pytest.mark.anyio
    async def test_create_melding(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") > 0
        assert data.get("text") == "This is a test melding."
        assert data.get("state") == MeldingStates.NEW
        assert data.get("classification") is None
        assert data.get("token") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None
        public_id = data.get("public_id")
        assert isinstance(public_id, str)
        assert len(public_id) == 6

    @pytest.mark.anyio
    async def test_create_melding_with_duplicate_public_id(
        self, app: FastAPI, client: AsyncClient, melding: Melding, public_id_generator_override: None
    ) -> None:
        response = await client.post(app.url_path_for(self.ROUTE_NAME_CREATE), json={"text": "This is a test melding."})

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data.get("id") > 0
        assert data.get("text") == "This is a test melding."
        assert data.get("state") == MeldingStates.NEW
        assert data.get("classification") is None
        assert data.get("token") is not None
        assert data.get("created_at") is not None
        assert data.get("updated_at") is not None
        assert data.get("public_id") == "MELPUB"

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
        assert data.get("classification").get("id") == classification.id
        assert data.get("classification").get("name") == classification.name

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

    @pytest.mark.anyio
    async def test_list_in_area_filter_invalid_geojson(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"in_area": "not_geo_json"})

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_locations",
        [
            (
                "POINT(4.898451690545197 52.37256509259712)",  # Barndesteeg 1B, Stadsdeel: Centrum
                "POINT(4.938320969227033 52.40152495315581)",  # Bakkerswaal 30, Stadsdeel: Noord
                "POINT(4.872746743968191 52.3341878625198)",  # Ennemaborg 7, Stadsdeel: Zuid
                "POINT(4.7765014635225835 52.37127670396132)",  # Osdorperweg 686, Stadsdeel: Nieuw-West
            )
        ],
    )
    async def test_list_in_area_filter(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        meldingen_with_location: list[Melding],
    ) -> None:
        with open("tests/resources/stadsdeel-centrum.json") as f:
            geojson = f.read()

        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"in_area": geojson})

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

        melding = meldingen_with_location[0]
        melding_response = body[0]

        assert melding_response.get("text") == melding.text

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_states",
        [
            (
                MeldingStates.NEW,
                MeldingStates.NEW,
                MeldingStates.ATTACHMENTS_ADDED,
                MeldingStates.CLASSIFIED,
                MeldingStates.NEW,
                MeldingStates.PROCESSING,
                MeldingStates.SUBMITTED,
                MeldingStates.NEW,
            )
        ],
    )
    async def test_list_state_filter(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        meldingen_with_different_states: list[Melding],
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME), params={"state": MeldingStates.NEW})

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 4

        melding = meldingen_with_different_states[0]
        melding_response = body[0]

        assert melding_response.get("state") == melding.state

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "melding_states, melding_locations",
        [
            (
                [
                    MeldingStates.NEW,
                    MeldingStates.NEW,
                    MeldingStates.NEW,
                    MeldingStates.PROCESSING,
                    MeldingStates.NEW,
                    MeldingStates.NEW,
                    MeldingStates.NEW,
                    MeldingStates.NEW,
                ],
                [
                    "POINT(4.898451690545197 52.37256509259712)",  # Barndesteeg 1B, Stadsdeel: Centrum
                    "POINT(4.938320969227033 52.40152495315581)",  # Bakkerswaal 30, Stadsdeel: Noord
                    "POINT(4.872746743968191 52.3341878625198)",  # Ennemaborg 7, Stadsdeel: Zuid
                    "POINT(4.898451690545197 52.37256509259712)",  # Barndesteeg 1B, Stadsdeel: Centrum
                    "POINT(4.7765014635225835 52.37127670396132)",  # Osdorperweg 686, Stadsdeel: Nieuw-West
                    "POINT(4.898451690545197 52.37256509259712)",  # Barndesteeg 1B, Stadsdeel: Centrum
                    "POINT(4.7765014635225835 52.37127670396132)",  # Osdorperweg 686, Stadsdeel: Nieuw-West
                    "POINT(4.898451690545197 52.37256509259712)",  # Barndesteeg 1B, Stadsdeel: Centrum
                ],
            )
        ],
    )
    async def test_list_with_state_and_in_area_filter(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        meldingen_with_different_states_and_locations: list[Melding],
    ) -> None:
        with open("tests/resources/stadsdeel-centrum.json") as f:
            geojson = f.read()

        response = await client.get(
            app.url_path_for(self.ROUTE_NAME), params={"in_area": geojson, "state": MeldingStates.NEW}
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 3

        melding = meldingen_with_different_states_and_locations[0]
        melding_response = body[0]

        assert melding_response.get("text") == melding.text


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
        [
            "melding_text",
            "melding_street",
            "melding_house_number",
            "melding_house_number_addition",
            "melding_postal_code",
            "melding_city",
        ],
        [
            ("Er ligt poep op de stoep.", "Amstel", 1, None, "1011PN", "Amsterdam"),
            ("Er is een matras naast de prullenbak gedumpt.", "Stationsplein", 35, "D", "1012AB", "Amsterdam"),
        ],
        indirect=True,
    )
    async def test_retrieve_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=melding.id))

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == melding.text
        assert body.get("state") == MeldingStates.NEW
        assert body.get("classification") is None
        assert body.get("geo_location", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("public_id") == melding.public_id
        assert body.get("street") == melding.street
        assert body.get("house_number") == melding.house_number
        assert body.get("house_number_addition") == melding.house_number_addition
        assert body.get("postal_code") == melding.postal_code
        assert body.get("city") == melding.city

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

    def get_extra_path_params(self) -> dict[str, Any]:
        return {}

    @pytest.mark.anyio
    async def test_token_missing(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1, **self.get_extra_path_params()),
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
            app.url_path_for(self.get_route_name(), melding_id=melding.id, **self.get_extra_path_params()),
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
            app.url_path_for(self.get_route_name(), melding_id=melding.id, **self.get_extra_path_params()),
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

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification", "") is None

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
        assert body.get("classification").get("id") == classification.id
        assert body.get("classification").get("name") == classification.name
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("public_id") == melding.public_id

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("My melding text", MeldingStates.QUESTIONS_ANSWERED, "supersecretToken", "classification1")],
    )
    async def test_update_melding_with_answers_causing_reclassification_that_fails(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_answers: Melding,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
            json={"text": "classification2"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification", "") is None

        results = await db_session.execute(select(Answer).where(Answer.melding_id == melding_with_answers.id))
        answers = results.scalars().all()

        assert len(answers) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("My melding text", MeldingStates.QUESTIONS_ANSWERED, "supersecretToken", "classification1")],
    )
    async def test_update_melding_with_answers_causing_reclassification_that_succeeds(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_answers: Melding,
        db_session: AsyncSession,
    ) -> None:
        classification2 = Classification("classification2")
        db_session.add(classification2)
        await db_session.commit()

        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
            json={"text": "classification2"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("id") == classification2.id
        assert body.get("classification").get("name") == classification2.name

        results = await db_session.execute(select(Answer).where(Answer.melding_id == melding_with_answers.id))
        answers = results.scalars().all()

        assert len(answers) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("My melding text", MeldingStates.QUESTIONS_ANSWERED, "supersecretToken", "classification1")],
    )
    async def test_update_melding_with_answers_when_classification_remains_the_same(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_answers: Melding,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
            json={"text": "classification1"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("name") == "classification1"

        results = await db_session.execute(select(Answer).where(Answer.melding_id == melding_with_answers.id))
        answers = results.scalars().all()

        assert len(answers) == 10

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_geo_location", "melding_token"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.NEW,
                "POINT(52.3680 4.8970)",
                "supersecrettoken",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_removes_location_after_reclassification(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        classification_with_asset_type: Classification,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": melding.token},
            json={"text": classification_with_asset_type.name},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("name") == classification_with_asset_type.name
        assert body.get("geo_location") == None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_geo_location", "melding_token"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "POINT(52.3680 4.8970)",
                "supersecrettoken",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_removes_assets_after_reclassification_but_keeps_location(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification_with_asset_type: Melding,
        db_session: AsyncSession,
    ) -> None:
        old_assets = await melding_with_classification_with_asset_type.awaitable_attrs.assets

        assert len(old_assets) == 1

        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification_with_asset_type.id),
            params={"token": melding_with_classification_with_asset_type.token},
            json={"text": "new classification"},
        )
        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification") is None
        assert body.get("geo_location").get("geometry").get("coordinates") == [52.3680, 4.8970]

        new_assets = await melding_with_classification_with_asset_type.awaitable_attrs.assets

        assert len(new_assets) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_geo_location", "melding_token"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.LOCATION_SUBMITTED,
                "POINT(52.3680 4.8970)",
                "supersecrettoken",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_retains_assets_after_reclassification_with_same_asset_type_but_removes_location(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification_with_asset_type: Melding,
        db_session: AsyncSession,
    ) -> None:
        old_assets = await melding_with_classification_with_asset_type.awaitable_attrs.assets

        assert len(old_assets) == 1

        classification: Classification = (
            await melding_with_classification_with_asset_type.awaitable_attrs.classification
        )

        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification_with_asset_type.id),
            params={"token": melding_with_classification_with_asset_type.token},
            json={"text": classification.name},
        )
        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("name") == classification.name
        assert body.get("geo_location") is None

        new_assets = await melding_with_classification_with_asset_type.awaitable_attrs.assets

        assert len(new_assets) == 1

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.NEW,
                "supersecrettoken",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_retains_none_location_after_reclassification(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        classification_with_asset_type: Classification,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": melding.token},
            json={"text": classification_with_asset_type.name},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("name") == classification_with_asset_type.name
        assert body.get("geo_location") is None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_geo_location", "melding_token", "classification_name"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.NEW,
                "POINT(52.3680 4.8970)",
                "supersecrettoken",
                "classification1",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_retains_location_after_reclassification_without_asset_type(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        classification: Classification,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding.id),
            params={"token": melding.token},
            json={"text": classification.name},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("classification").get("name") == classification.name
        assert body.get("geo_location").get("geometry").get("coordinates") == [52.3680, 4.8970]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_geo_location", "melding_token"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.NEW,
                "POINT(52.3680 4.8970)",
                "supersecrettoken",
            )
        ],
        indirect=True,
    )
    async def test_update_melding_removes_location_after_reclassification_with_same_asset_type(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification_with_asset_type: Melding,
        db_session: AsyncSession,
    ) -> None:
        response = await client.patch(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification_with_asset_type.id),
            params={"token": melding_with_classification_with_asset_type.token},
            json={"text": "test_classification"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("geo_location") is None


class TestMeldingAnswerQuestions(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:answer_questions"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification")],
        indirect=True,
    )
    async def test_answer_questions(
        self, app: FastAPI, client: AsyncClient, melding_with_classification: Melding, form_with_classification: Form
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_classification.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding_with_classification.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "is_required"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification", True)],
        indirect=True,
    )
    async def test_answer_questions_with_required_answered(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_answers: Melding,
    ) -> None:

        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_answers.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_answers.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding_with_answers.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "is_required", "classification_name"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.CLASSIFIED,
                "supersecrettoken",
                True,
                "test_classification",
            )
        ],
        indirect=["is_required", "classification_name"],
    )
    async def test_answer_questions_without_answering_required_questions(
        self, app: FastAPI, client: AsyncClient, melding_with_classification: Melding, form_with_classification: Form
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "All required questions must be answered first"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name", "is_required"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification", True)],
        indirect=True,
    )
    async def test_answer_questions_with_some_required_answered(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_some_answers: Melding,
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_some_answers.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()

        assert body.get("detail") == "All required questions must be answered first"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "classification_name"],
        [("De restafvalcontainer is vol.", MeldingStates.CLASSIFIED, "supersecrettoken", "test_classification")],
        indirect=True,
    )
    async def test_answer_questions_with_no_form_for_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
    ) -> None:
        response = await client.put(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_classification.id),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.QUESTIONS_ANSWERED
        assert body.get("created_at") == melding_with_classification.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding_with_classification.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestMeldingAddAttachments(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-attachments"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.LOCATION_SUBMITTED, "supersecrettoken")],
        indirect=True,
    )
    async def test_add_attachments(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.put(
            app.url_path_for(self.get_route_name(), melding_id=melding.id), params={"token": "supersecrettoken"}
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.ATTACHMENTS_ADDED
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

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


class TestMeldingSubmitLocation(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:submit-location"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_geo_location"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.QUESTIONS_ANSWERED,
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
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("De restafvalcontainer is vol.", MeldingStates.QUESTIONS_ANSWERED, "supersecrettoken")],
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


class TestMeldingProcess(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:process"

    def get_method(self) -> str:
        return "PUT"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"], [("Er ligt poep op de stoep.", MeldingStates.SUBMITTED)], indirect=True
    )
    async def test_process_melding(self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding) -> None:
        response = await client.request(
            self.get_method(), app.url_path_for(self.get_route_name(), melding_id=melding.id)
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.PROCESSING
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

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
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_email", "mailpit_api"],
        [("Er ligt poep op de stoep.", MeldingStates.PROCESSING, "me@example.com", "http://mailpit:8025")],
        indirect=True,
    )
    async def test_complete_melding_with_mail_text(
        self, app: FastAPI, client: AsyncClient, auth_user: None, melding: Melding, mailpit_api: API
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            json={"mail_body": "TEST MAIL TEXT"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert body.get("state") == MeldingStates.COMPLETED
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        messages = mailpit_api.get_messages()
        assert messages.total == 1

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

        text = "dit is het antwoord op de vraag"
        data = {"text": text}

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
        assert data.get("text") == text
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
        [
            "melding_text",
            "melding_state",
            "melding_token",
            "classification_name",
            "jsonlogic",
            "validation_err_message",
        ],
        [
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"!=":[{"var": "text"}, "dit is het antwoord op de vraag"]}',
                "Input is not valid",
            ),
            (
                "klacht over iets",
                MeldingStates.CLASSIFIED,
                "supersecuretoken",
                "test_classification",
                '{"if": [{"<=": [{"var": "value.length"},20]}, true, "Max 20 characters"]}',
                "Max 20 characters",
            ),
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
        validation_err_message: str,
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
        msg = body.get("detail")[0].get("msg")
        assert msg == validation_err_message

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


class TestMeldingUpdateAnswer(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:update-answer"

    def get_method(self) -> str:
        return "PATCH"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"text": "This is the answer"}

    @override
    def get_extra_path_params(self) -> dict[str, Any]:
        return {"answer_id": 123}

    @pytest.mark.anyio
    async def test_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=123, answer_id=456),
            params={"token": "supersecuretoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("melding_token", ["supersecrettoken"])
    @pytest.mark.anyio
    async def test_answer_not_found(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id, answer_id=456),
            params={"token": melding.token},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_answer_does_not_belong_to_melding(
        self, app: FastAPI, client: AsyncClient, melding_with_some_answers: Melding, db_session: AsyncSession
    ) -> None:
        melding = Melding("Text", token="supersecrettoken")
        melding.public_id = "PUB123"
        db_session.add(melding)
        await db_session.commit()

        result = await db_session.execute(select(Answer))
        answers = result.scalars().all()
        assert len(answers) > 0

        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id, answer_id=answers[0].id),
            params={"token": melding.token},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("msg") == "Answer does not belong to melding"

    @pytest.mark.parametrize(
        ["melding_token", "classification_name", "jsonlogic"],
        [
            (
                "supersecrettoken",
                "test_classification",
                '{"if": [{"==": [{"var": "text"},"test"]}, true, "Not equal"]}',
            )
        ],
        indirect=["classification_name", "jsonlogic"],
    )
    @pytest.mark.anyio
    async def test_answer_text_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
        db_session: AsyncSession,
    ) -> None:
        questions = await form_with_classification.awaitable_attrs.questions
        assert len(questions) == 1

        answer = Answer(text="This is the answer", question=questions[0], melding=melding_with_classification)
        db_session.add(answer)
        await db_session.commit()

        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_classification.id, answer_id=answer.id),
            params={"token": melding_with_classification.token},
            json={"text": "This is another answer"},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

        body = response.json()
        detail = body.get("detail")
        assert len(detail) == 1
        assert detail[0].get("msg") == "Not equal"
        assert detail[0].get("input") == {"text": "This is another answer"}

    @pytest.mark.parametrize(
        ["melding_token", "classification_name", "jsonlogic"],
        [
            (
                "supersecrettoken",
                "test_classification",
                '{"if": [{"==": [{"var": "text"},"This is another answer"]}, true, "Not equal"]}',
            )
        ],
        indirect=["classification_name", "jsonlogic"],
    )
    @pytest.mark.anyio
    async def test_update_answer(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding_with_classification: Melding,
        form_with_classification: Form,
        db_session: AsyncSession,
    ) -> None:
        questions = await form_with_classification.awaitable_attrs.questions
        assert len(questions) == 1

        answer = Answer(text="This is the answer", question=questions[0], melding=melding_with_classification)
        db_session.add(answer)
        await db_session.commit()

        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_classification.id, answer_id=answer.id),
            params={"token": melding_with_classification.token},
            json={"text": "This is another answer"},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == answer.id
        assert body.get("text") == "This is another answer"
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None


class TestMeldingUploadAttachment:
    ROUTE_NAME_CREATE: Final[str] = "melding:attachment"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "filename"],
        [
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.jpg"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.png"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam-logo.webp"),
            ("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken", "amsterdam logo.webp"),
        ],
    )
    async def test_upload_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        db_session: AsyncSession,
        container_client: ContainerClient,
        azure_container_client_override: None,
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

        await db_session.refresh(melding)
        attachments = await melding.awaitable_attrs.attachments
        assert len(attachments) == 0

    @pytest.mark.anyio
    async def test_upload_attachment_melding_not_found(
        self,
        app: FastAPI,
        client: AsyncClient,
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

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token"],
        [("klacht over iets", MeldingStates.CLASSIFIED, "supersecuretoken")],
    )
    async def test_upload_attachment_token_missing(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
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

    @pytest.mark.anyio
    async def test_upload_attachment_unauthorized_token_invalid(
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
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
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
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


class TestMeldingDownloadAttachment(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachment-download"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    @override
    def get_extra_path_params(self) -> dict[str, Any]:
        return {"attachment_id": 456}

    @pytest.mark.anyio
    async def test_download_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

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
        melding.public_id = "MELPUB"

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
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        azure_container_client_override: None,
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
        assert response.headers.get("content-type") == "image/jpeg"

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
        azure_container_client_override: None,
        db_session: AsyncSession,
    ) -> None:
        attachment.optimized_path = f"/tmp/{uuid4()}/optimized.webp"
        attachment.optimized_media_type = "image/webp"
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
        assert response.headers.get("content-type") == "image/webp"

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
        azure_container_client_override: None,
        db_session: AsyncSession,
    ) -> None:
        attachment.thumbnail_path = f"/tmp/{uuid4()}/thumbnail.webp"
        attachment.thumbnail_media_type = "image/webp"
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
        assert response.headers.get("content-type") == "image/webp"


class TestMeldingListAttachments(BaseUnauthorizedTest):
    ROUTE_NAME: Final[str] = "melding:attachments"
    PATH_PARAMS: dict[str, Any] = {"melding_id": 1}

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return self.PATH_PARAMS

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecuretoken",)])
    async def test_list_attachments(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id))

        assert response.status_code == HTTP_200_OK

        attachments = await melding_with_attachments.awaitable_attrs.attachments
        body = response.json()

        assert len(attachments) == len(body)

    @pytest.mark.anyio
    async def test_list_attachments_with_non_existing_melding(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(app.url_path_for(self.ROUTE_NAME, melding_id=123))

        assert response.status_code == HTTP_200_OK
        body = response.json()

        assert len(body) == 0


class TestMelderMeldingListAttachments(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachments_melder"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_melder_list_attachments_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=123),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecuretoken",)])
    async def test_melder_list_attachments(
        self, app: FastAPI, client: AsyncClient, melding_with_attachments: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for(self.ROUTE_NAME, melding_id=melding_with_attachments.id),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_200_OK

        attachments = await melding_with_attachments.awaitable_attrs.attachments
        body = response.json()

        assert len(attachments) == len(body)


class TestMeldingDeleteAttachmentAction(BaseTokenAuthenticationTest):
    ROUTE_NAME: Final[str] = "melding:attachment-delete"

    def get_route_name(self) -> str:
        return self.ROUTE_NAME

    def get_method(self) -> str:
        return "DELETE"

    @override
    def get_extra_path_params(self) -> dict[str, Any]:
        return {"attachment_id": 456}

    @pytest.mark.anyio
    async def test_delete_attachment_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.delete(
            app.url_path_for(self.ROUTE_NAME, melding_id=123, attachment_id=456),
            params={"token": "supersecuretoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

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
        melding.public_id = "MELPUB"

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
        self,
        app: FastAPI,
        client: AsyncClient,
        attachment: Attachment,
        container_client: ContainerClient,
        azure_container_client_override: None,
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
            assert await blob_client.exists() is False


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
        self,
        app: FastAPI,
        client: AsyncClient,
        melding: Melding,
        geojson: dict[str, Any],
        address_api_client_override: None,
        address_api_mock_data: dict[str, Any],
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
        assert body.get("city") == address_api_mock_data.get("woonplaatsnaam")
        assert body.get("street") == address_api_mock_data.get("straatnaam")
        assert body.get("house_number") == address_api_mock_data.get("huisnummer")
        assert body.get("house_number_addition") == address_api_mock_data.get("huisletter")

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

    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "geojson_geometry"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                {
                    "type": "Point",
                },
            )
        ],
        indirect=True,
    )
    async def test_add_location_no_coordinates(
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

        assert len(detail) == 1
        assert detail[0].get("msg") == "Field required"
        assert detail[0].get("loc") == ["body", "geometry", "coordinates"]


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


class TestMeldingContactInfoAdded(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-contact-info"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state", "melding_token", "melding_email", "melding_phone"],
        [
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                None,
                None,
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                "melder@example.com",
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
                "supersecrettoken",
                None,
                "+31612345678",
            ),
            (
                "De restafvalcontainer is vol.",
                MeldingStates.ATTACHMENTS_ADDED,
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
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    @pytest.mark.anyio
    async def test_contact_info_added_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=1),
            params={"token": "supersecrettoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestMeldingListQuestionsAnswers(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:answers"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers_melding_without_answers(
        self, app: FastAPI, client: AsyncClient, melding: Melding, auth_user: None
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers(
        self, app: FastAPI, client: AsyncClient, melding_with_answers: Melding, auth_user: None
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 10

        question_ids = []
        for answer_output in body:
            question = answer_output.get("question")
            question_ids.append(question.get("id"))

        assert sorted(question_ids) == question_ids

        answer = body[0]
        assert answer.get("id") > 0
        assert answer.get("text") == "Answer 0"
        assert answer.get("created_at") is not None
        assert answer.get("updated_at") is not None

        question = answer.get("question")
        assert question is not None
        assert question.get("id") > 0
        assert question.get("text") == "Question 0"
        assert question.get("created_at") is not None
        assert question.get("updated_at") is not None


class TestMelderMeldingListQuestionsAnswers(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:answers_melder"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    async def test_list_answers_melding_not_found(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=999),
            params={"token": "nonexistingtoken"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers_melding_without_answers(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 0

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_list_answers(self, app: FastAPI, client: AsyncClient, melding_with_answers: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding_with_answers.id),
            params={"token": melding_with_answers.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()

        assert isinstance(body, list)
        assert len(body) == 10

        question_ids = []
        for answer_output in body:
            question = answer_output.get("question")
            question_ids.append(question.get("id"))

        assert sorted(question_ids) == question_ids

        answer = body[0]
        assert answer.get("id") > 0
        assert answer.get("text") == "Answer 0"
        assert answer.get("created_at") is not None
        assert answer.get("updated_at") is not None

        question = answer.get("question")
        assert question is not None
        assert question.get("id") > 0
        assert question.get("text") == "Question 0"
        assert question.get("created_at") is not None
        assert question.get("updated_at") is not None


class TestMelderMeldingRetrieve(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:retrieve_melder"

    def get_method(self) -> str:
        return "GET"

    @pytest.mark.anyio
    @pytest.mark.parametrize("melding_token", ["supersecrettoken"])
    async def test_retrieve_melding(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") == melding.id
        assert body.get("text") == melding.text
        assert body.get("state") == MeldingStates.NEW
        assert body.get("classification") is None
        assert body.get("geo_location", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None
        assert body.get("created_at") == melding.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        assert body.get("updated_at") == melding.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestMeldingSubmit(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:submit"

    def get_method(self) -> str:
        return "PUT"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_state", "melding_token", "melding_email", "mailpit_api"],
        [(MeldingStates.CONTACT_INFO_ADDED, "supersecrettoken", "melder@example.com", "http://mailpit:8025")],
        indirect=True,
    )
    async def test_submit_melding(self, app: FastAPI, client: AsyncClient, melding: Melding, mailpit_api: API) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("state") == MeldingStates.SUBMITTED

        messages = mailpit_api.get_messages()
        assert messages.total == 1

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_state", "melding_token"],
        [
            (MeldingStates.NEW, "supersecrettoken"),
            (MeldingStates.CLASSIFIED, "supersecrettoken"),
            (MeldingStates.QUESTIONS_ANSWERED, "supersecrettoken"),
            (MeldingStates.ATTACHMENTS_ADDED, "supersecrettoken"),
            (MeldingStates.LOCATION_SUBMITTED, "supersecrettoken"),
            (MeldingStates.SUBMITTED, "supersecrettoken"),
            (MeldingStates.PROCESSING, "supersecrettoken"),
            (MeldingStates.COMPLETED, "supersecrettoken"),
        ],
    )
    async def test_submit_melding_wrong_from_state(self, app: FastAPI, client: AsyncClient, melding: Melding) -> None:
        response = await client.request(
            self.get_method(),
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": melding.token},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST

        body = response.json()
        assert body.get("detail") == "Transition not allowed from current state"


class TestMeldingAddAsset(BaseTokenAuthenticationTest):
    def get_route_name(self) -> str:
        return "melding:add-asset"

    def get_method(self) -> str:
        return "POST"

    @override
    def get_json(self) -> dict[str, Any] | None:
        return {"external_id": "some_external_id", "asset_type_id": 123}

    @pytest.mark.anyio
    async def test_add_asset_to_melding_that_does_not_exist(self, app: FastAPI, client: AsyncClient) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name(), melding_id=123),
            params={"token": "supersecrettoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Melding not found"

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_add_asset_with_asset_type_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, melding: Melding
    ) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
            json=self.get_json(),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

        body = response.json()
        assert body.get("detail") == "Failed to find asset type with id 123"

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_add_asset_that_does_not_exist(
        self, app: FastAPI, client: AsyncClient, melding: Melding, asset_type: AssetType
    ) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
            json={"external_id": "my_external_id", "asset_type_id": asset_type.id},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None
        assert body.get("public_id") == "PUBMEL"
        assert body.get("text") == "This is a test melding."
        assert body.get("state") == "new"
        assert body.get("classification", "") is None
        assert body.get("geo_location", "") is None
        assert body.get("street", "") is None
        assert body.get("house_number", "") is None
        assert body.get("house_number_addition", "") is None
        assert body.get("postal_code", "") is None
        assert body.get("city", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_token"], [("supersecrettoken",)])
    async def test_add_asset_that_already_exists(
        self, app: FastAPI, client: AsyncClient, melding: Melding, asset: Asset
    ) -> None:
        response = await client.post(
            app.url_path_for(self.get_route_name(), melding_id=melding.id),
            params={"token": "supersecrettoken"},
            json={"external_id": asset.external_id, "asset_type_id": asset.type_id},
        )

        assert response.status_code == HTTP_200_OK

        body = response.json()
        assert body.get("id") > 0
        assert body.get("created_at") is not None
        assert body.get("updated_at") is not None
        assert body.get("public_id") == "PUBMEL"
        assert body.get("text") == "This is a test melding."
        assert body.get("state") == "new"
        assert body.get("classification", "") is None
        assert body.get("geo_location", "") is None
        assert body.get("street", "") is None
        assert body.get("house_number", "") is None
        assert body.get("house_number_addition", "") is None
        assert body.get("postal_code", "") is None
        assert body.get("city", "") is None
        assert body.get("email", "") is None
        assert body.get("phone", "") is None
