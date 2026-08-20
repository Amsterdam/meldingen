from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core.statemachine import MeldingStates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from meldingen.models import Classification, Form, Melding, Note, TextAnswer, User
from tests.api.v1.endpoints.base import BaseUnauthorizedTest

ROUTE = "melding:reclassification"

# The states a melding may be reclassified from. Everything else is refused: a melding that is
# completed or canceled is closed, and one still in the melder's flow has not reached the
# backoffice yet.
RECLASSIFIABLE_STATES = [
    MeldingStates.SUBMITTED,
    MeldingStates.PROCESSING_REQUESTED,
    MeldingStates.PROCESSING,
    MeldingStates.PLANNED,
    MeldingStates.REOPEN_REQUESTED,
    MeldingStates.REOPENED,
]

NON_RECLASSIFIABLE_STATES = [
    MeldingStates.COMPLETED,
    MeldingStates.CANCELED,
    MeldingStates.NEW,
    MeldingStates.CLASSIFIED,
    MeldingStates.QUESTIONS_ANSWERED,
    MeldingStates.LOCATION_SUBMITTED,
    MeldingStates.ATTACHMENTS_ADDED,
    MeldingStates.CONTACT_INFO_ADDED,
]


@pytest.fixture
async def new_classification(db_session: AsyncSession) -> Classification:
    classification = Classification(name="the new classification")
    db_session.add(classification)
    await db_session.commit()

    return classification


class TestReclassifyMeldingUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return ROUTE

    def get_method(self) -> str:
        return "POST"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}


class TestReclassifyMelding:
    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.PROCESSING,)], indirect=True)
    async def test_reclassify_assigns_new_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding_with_classification: Melding,
        new_classification: Classification,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding_with_classification.id),
            json={"classification_id": new_classification.id, "reason": "Hoort bij een andere categorie"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["classification"]["id"] == new_classification.id

        await db_session.refresh(melding_with_classification)
        assert melding_with_classification.classification_id == new_classification.id

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(state,) for state in RECLASSIFIABLE_STATES], indirect=True)
    async def test_reclassify_sets_state_to_submitted(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        new_classification: Classification,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "Verkeerd geclassificeerd"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["state"] == MeldingStates.SUBMITTED

        await db_session.refresh(melding)
        assert melding.state == MeldingStates.SUBMITTED

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.PLANNED,)], indirect=True)
    async def test_reclassify_stores_reason_as_note_referencing_new_classification(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        new_classification: Classification,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "Dit is werk voor een andere afdeling"},
        )

        assert response.status_code == HTTP_200_OK

        notes = (await db_session.execute(select(Note).where(Note.melding_id == melding.id))).scalars().all()
        assert len(notes) == 1

        note = notes[0]
        assert note.text == "Dit is werk voor een andere afdeling"
        assert note.classification_id == new_classification.id
        assert note.user_id == auth_behandelaar.id

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.PROCESSING,)], indirect=True)
    async def test_reclassify_keeps_assets_supplied_by_the_melder(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding_with_classification_with_asset_type: Melding,
        new_classification: Classification,
    ) -> None:
        """Unlike the melder's reclassification, a backoffice reclassification keeps the assets,
        even though the new classification has no asset type at all."""
        melding = melding_with_classification_with_asset_type
        assert len(await melding.awaitable_attrs.assets) == 1

        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_200_OK

        await db_session.refresh(melding)
        assert len(await melding.awaitable_attrs.assets) == 1

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.PROCESSING,)], indirect=True)
    async def test_reclassify_keeps_answers_supplied_by_the_melder(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        form: Form,
        new_classification: Classification,
    ) -> None:
        component = (await form.awaitable_attrs.components)[0]
        question = await component.awaitable_attrs.question
        db_session.add(TextAnswer(question=question, melding=melding, text="Het antwoord van de melder"))
        await db_session.commit()

        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_200_OK

        answer_count = await db_session.scalar(
            select(func.count(TextAnswer.id)).where(TextAnswer.melding_id == melding.id)
        )
        assert answer_count == 1

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(state,) for state in NON_RECLASSIFIABLE_STATES], indirect=True)
    async def test_reclassify_from_disallowed_state_returns_400(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding_with_classification: Melding,
        new_classification: Classification,
        melding_state: str,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding_with_classification.id),
            json={"classification_id": new_classification.id, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Melding may not be reclassified from current state"

        # A refused reclassification leaves neither the melding nor a note behind.
        await db_session.refresh(melding_with_classification)
        assert melding_with_classification.state == melding_state
        assert melding_with_classification.classification_id != new_classification.id

        notes = (
            (await db_session.execute(select(Note).where(Note.melding_id == melding_with_classification.id)))
            .scalars()
            .all()
        )
        assert len(notes) == 0

    @pytest.mark.anyio
    async def test_reclassify_nonexistent_melding_returns_404(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        new_classification: Classification,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=999999),
            json={"classification_id": new_classification.id, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Failed to find melding with id 999999"

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.SUBMITTED,)], indirect=True)
    async def test_reclassify_to_nonexistent_classification_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, melding: Melding
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": 999999, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Failed to find classification with id 999999"

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.SUBMITTED,)], indirect=True)
    async def test_reclassify_to_deleted_classification_returns_404(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        new_classification: Classification,
    ) -> None:
        """A soft-deleted classification is no longer offered, so a melding cannot be moved to it."""
        new_classification.deleted_at = func.now()
        db_session.add(new_classification)
        await db_session.commit()

        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "Andere categorie"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.SUBMITTED,)], indirect=True)
    @pytest.mark.parametrize(
        ["body", "expected_loc"],
        [
            ({"reason": "Andere categorie"}, ["body", "classification_id"]),
            ({"classification_id": 0, "reason": "Andere categorie"}, ["body", "classification_id"]),
            ({"classification_id": 1}, ["body", "reason"]),
            ({"classification_id": 1, "reason": ""}, ["body", "reason"]),
            ({"classification_id": 1, "reason": "   "}, ["body", "reason"]),
            ({"classification_id": 1, "reason": "a" * 1001}, ["body", "reason"]),
        ],
    )
    async def test_reclassify_with_invalid_input_returns_422(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        body: dict[str, Any],
        expected_loc: list[str],
    ) -> None:
        response = await client.post(app.url_path_for(ROUTE, melding_id=melding.id), json=body)

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == expected_loc

    @pytest.mark.anyio
    @pytest.mark.parametrize(["melding_state"], [(MeldingStates.SUBMITTED,)], indirect=True)
    async def test_reclassify_with_reason_at_the_limit_is_accepted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        new_classification: Classification,
    ) -> None:
        response = await client.post(
            app.url_path_for(ROUTE, melding_id=melding.id),
            json={"classification_id": new_classification.id, "reason": "a" * 1000},
        )

        assert response.status_code == HTTP_200_OK
