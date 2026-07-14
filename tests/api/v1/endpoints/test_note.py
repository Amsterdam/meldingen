from datetime import datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from meldingen.models import Melding, Note, User
from tests.api.v1.endpoints.base import BaseUnauthorizedTest


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


@pytest.fixture
async def note(db_session: AsyncSession, melding: Melding, user: User) -> Note:
    note = Note(text="An existing note", melding=melding, user=user)
    db_session.add(note)
    await db_session.commit()
    return note


class TestRetrieveNoteUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:retrieve-note"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1, "note_id": 1}


class TestRetrieveNote:
    @pytest.mark.anyio
    async def test_retrieve_note_returns_note_with_user(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        user: User,
        note: Note,
    ) -> None:
        response = await client.get(
            app.url_path_for("melding:retrieve-note", melding_id=melding.id, note_id=note.id),
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["id"] == note.id
        assert data["text"] == "An existing note"
        assert data["melding_id"] == melding.id
        assert "created_at" in data
        assert "updated_at" in data

        assert data["user"]["id"] == user.id
        assert data["user"]["email"] == user.email
        assert data["user"]["username"] == user.username
        assert "created_at" in data["user"]
        assert "updated_at" in data["user"]

    @pytest.mark.anyio
    async def test_retrieve_note_from_nonexistent_melding_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, note: Note
    ) -> None:
        response = await client.get(
            app.url_path_for("melding:retrieve-note", melding_id=999999, note_id=note.id),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_retrieve_nonexistent_note_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for("melding:retrieve-note", melding_id=melding.id, note_id=999999),
        )

        assert response.status_code == HTTP_404_NOT_FOUND


class TestUpdateNoteUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:update-note"

    def get_method(self) -> str:
        return "PATCH"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1, "note_id": 1}


class TestUpdateNote:
    @pytest.mark.anyio
    async def test_update_note_updates_text(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        note: Note,
    ) -> None:
        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=melding.id, note_id=note.id),
            json={"text": "updated **text**"},
        )

        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["id"] == note.id
        assert data["text"] == "updated **text**"
        assert data["melding_id"] == melding.id

        persisted = (await db_session.execute(select(Note).where(Note.id == note.id))).scalar_one()
        assert persisted.text == "updated **text**"

    @pytest.mark.anyio
    async def test_update_note_allows_empty_text(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        note: Note,
    ) -> None:
        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=melding.id, note_id=note.id),
            json={"text": ""},
        )

        assert response.status_code == HTTP_200_OK
        assert response.json()["text"] == ""

    @pytest.mark.anyio
    async def test_update_note_from_nonexistent_melding_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, note: Note
    ) -> None:
        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=999999, note_id=note.id),
            json={"text": "whatever"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_nonexistent_note_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, melding: Melding
    ) -> None:
        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=melding.id, note_id=999999),
            json={"text": "whatever"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_update_note_by_non_owner_returns_403(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
    ) -> None:
        other_user = User(username="other", email="other@example.com")
        db_session.add(other_user)
        await db_session.commit()

        note = Note(text="not mine", melding=melding, user=other_user)
        db_session.add(note)
        await db_session.commit()

        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=melding.id, note_id=note.id),
            json={"text": "hacked"},
        )

        assert response.status_code == HTTP_403_FORBIDDEN

        persisted = (await db_session.execute(select(Note).where(Note.id == note.id))).scalar_one()
        assert persisted.text == "not mine"

    @pytest.mark.anyio
    async def test_update_note_with_plain_text_over_limit_returns_422(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_behandelaar: User,
        melding: Melding,
        note: Note,
    ) -> None:
        response = await client.patch(
            app.url_path_for("melding:update-note", melding_id=melding.id, note_id=note.id),
            json={"text": "a" * 3001},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == ["body", "text"]


class TestListNotesUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "melding:notes"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, Any]:
        return {"melding_id": 1}


class TestListNotes:
    @pytest.mark.anyio
    async def test_list_notes_from_nonexistent_melding_returns_404(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User
    ) -> None:
        response = await client.get(app.url_path_for("melding:notes", melding_id=999999))

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_list_notes_returns_empty_list_when_melding_has_no_notes(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, melding: Melding
    ) -> None:
        response = await client.get(app.url_path_for("melding:notes", melding_id=melding.id))

        assert response.status_code == HTTP_200_OK
        assert response.json() == []

    @pytest.mark.anyio
    async def test_list_notes_returns_notes_sorted_by_created_at(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        user: User,
    ) -> None:
        # Insert so that created_at order differs from insertion/id order, proving the
        # list is sorted on created_at and not on id.
        newer = Note(text="newer", melding=melding, user=user)
        newer.created_at = datetime(2025, 1, 2, 12, 0, 0)
        older = Note(text="older", melding=melding, user=user)
        older.created_at = datetime(2025, 1, 1, 12, 0, 0)
        db_session.add(newer)
        db_session.add(older)
        await db_session.commit()

        response = await client.get(app.url_path_for("melding:notes", melding_id=melding.id))

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert [note["text"] for note in data] == ["older", "newer"]

        first = data[0]
        assert first["melding_id"] == melding.id
        assert "id" in first
        assert "created_at" in first
        assert "updated_at" in first
        assert first["user"]["id"] == user.id
        assert first["user"]["email"] == user.email
        assert first["user"]["username"] == user.username
        assert "created_at" in first["user"]
        assert "updated_at" in first["user"]

    @pytest.mark.anyio
    async def test_list_notes_sorted_by_created_at_descending(
        self,
        app: FastAPI,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_behandelaar: User,
        melding: Melding,
        user: User,
    ) -> None:
        newer = Note(text="newer", melding=melding, user=user)
        newer.created_at = datetime(2025, 1, 2, 12, 0, 0)
        older = Note(text="older", melding=melding, user=user)
        older.created_at = datetime(2025, 1, 1, 12, 0, 0)
        db_session.add(newer)
        db_session.add(older)
        await db_session.commit()

        response = await client.get(
            app.url_path_for("melding:notes", melding_id=melding.id),
            params={"sort": '["created_at","DESC"]'},
        )

        assert response.status_code == HTTP_200_OK
        assert [note["text"] for note in response.json()] == ["newer", "older"]

    @pytest.mark.anyio
    async def test_list_notes_with_unknown_sort_attribute_returns_422(
        self, app: FastAPI, client: AsyncClient, auth_behandelaar: User, melding: Melding
    ) -> None:
        response = await client.get(
            app.url_path_for("melding:notes", melding_id=melding.id),
            params={"sort": '["does_not_exist","ASC"]'},
        )

        assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["detail"][0]["loc"] == ["query", "sort"]
