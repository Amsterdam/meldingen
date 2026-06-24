from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_CONTENT

from meldingen.authentication import authenticate_user
from meldingen.models import Melding, Note, User
from tests.api.v1.endpoints.base import BaseUnauthorizedTest


@pytest.fixture
def auth_behandelaar(app: FastAPI, user: User) -> User:
    """Authenticate every request as the given (persisted) Behandelaar user."""

    async def authenticate_user_override() -> User:
        return user

    app.dependency_overrides[authenticate_user] = authenticate_user_override

    return user


class TestAddNoteUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:add-note"

    def get_method(self) -> str:
        return "POST"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}


class TestAddNote:
    @pytest.mark.anyio
    async def test_add_note_returns_created_note(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=melding.id),
            json={"text": "This is a **note**"},
        )

        assert response.status_code == HTTP_201_CREATED

        data = response.json()
        assert data["text"] == "This is a **note**"
        assert data["melding_id"] == melding.id
        assert data["user_id"] == auth_behandelaar.id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        notes = (await db_session.execute(select(Note).where(Note.melding_id == melding.id))).scalars().all()
        assert len(notes) == 1
        assert notes[0].text == "This is a **note**"

    @pytest.mark.anyio
    async def test_add_note_to_nonexistent_melding_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User
    ) -> None:
        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=999999),
            json={"text": "A note"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_add_note_strips_whitespace(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=melding.id),
            json={"text": "  surrounded by whitespace  "},
        )

        assert response.status_code == HTTP_201_CREATED
        assert response.json()["text"] == "surrounded by whitespace"

    @pytest.mark.anyio
    @pytest.mark.parametrize("text", ["", "   ", "\n\t "])
    async def test_add_empty_note_returns_422(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        text: str,
    ) -> None:
        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=melding.id),
            json={"text": text},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == ["body", "text"]

    @pytest.mark.anyio
    async def test_add_note_without_text_returns_422(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        response = await client.post(app.url_path_for("melding:add-note", melding_id=melding.id), json={})

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.anyio
    async def test_add_note_with_plain_text_over_limit_returns_422(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=melding.id),
            json={"text": "a" * 3001},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == ["body", "text"]

    @pytest.mark.anyio
    async def test_add_note_with_markdown_over_limit_but_plain_text_under_is_accepted(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        # Bold markup makes the raw text exceed 3000 characters, while the rendered
        # plain text stays under the limit, so the note should be accepted.
        text = "**" + ("a" * 2999) + "**"
        assert len(text) > 3000

        response = await client.post(
            app.url_path_for("melding:add-note", melding_id=melding.id),
            json={"text": text},
        )

        assert response.status_code == HTTP_201_CREATED
        assert response.json()["text"] == text
