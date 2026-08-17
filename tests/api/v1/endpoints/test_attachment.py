from typing import Any, override
from uuid import uuid4

import pytest
from azure.storage.blob.aio import ContainerClient
from fastapi import FastAPI
from httpx import AsyncClient
from meldingen_core.statemachine import MeldingStates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

from meldingen.models import Attachment, User
from tests.api.v1.endpoints.base import BaseUnauthorizedTest


class TestDownloadAttachment(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "attachment:download"

    def get_method(self) -> str:
        return "GET"

    @override
    def get_path_params(self) -> dict[str, Any]:
        return {"id": 123}

    @pytest.mark.anyio
    async def test_download_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), id=456),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, attachment: Attachment
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attachment: Attachment,
        container_client: ContainerClient,
        azure_container_client_override: None,
    ) -> None:
        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/jpeg"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_optimized_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, attachment: Attachment
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
            params={"type": "optimized"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_optimized_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
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

        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
            params={"type": "optimized"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/webp"

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_thumbnail_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, attachment: Attachment
    ) -> None:
        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
            params={"type": "thumbnail"},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_download_thumbnail_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
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

        response = await client.get(
            app.url_path_for(self.get_route_name(), id=attachment.id),
            params={"type": "thumbnail"},
        )

        assert response.status_code == HTTP_200_OK
        assert response.text == "some data"
        assert response.headers.get("content-type") == "image/webp"


class TestDeleteAttachment(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "attachment:delete"

    def get_method(self) -> str:
        return "DELETE"

    @override
    def get_path_params(self) -> dict[str, Any]:
        return {"id": 123}

    @pytest.mark.anyio
    async def test_delete_attachment_attachment_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.get_route_name(), id=456),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_delete_attachment_file_not_found(
        self, app: FastAPI, client: AsyncClient, auth_user: None, attachment: Attachment
    ) -> None:
        response = await client.delete(
            app.url_path_for(self.get_route_name(), id=attachment.id),
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_delete_attachment(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attachment: Attachment,
        container_client: ContainerClient,
        azure_container_client_override: None,
        db_session: AsyncSession,
    ) -> None:
        attachment_id = attachment.id

        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        response = await client.delete(
            app.url_path_for(self.get_route_name(), id=attachment_id),
        )

        assert response.status_code == HTTP_204_NO_CONTENT

        async with blob_client:
            assert await blob_client.exists() is False

        assert await db_session.get(Attachment, attachment_id) is None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ["melding_text", "melding_state"],
        [("klacht over iets", MeldingStates.CLASSIFIED)],
        indirect=True,
    )
    async def test_delete_attachment_uploaded_by_colleague(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        attachment: Attachment,
        container_client: ContainerClient,
        azure_container_client_override: None,
        db_session: AsyncSession,
        user: User,
    ) -> None:
        """A behandelaar may also delete attachments that a colleague added."""
        attachment.user_id = user.id
        await db_session.commit()

        attachment_id = attachment.id

        blob_client = container_client.get_blob_client(attachment.file_path)
        async with blob_client:
            await blob_client.upload_blob(b"some data")

        response = await client.delete(
            app.url_path_for(self.get_route_name(), id=attachment_id),
        )

        assert response.status_code == HTTP_204_NO_CONTENT

        async with blob_client:
            assert await blob_client.exists() is False

        assert await db_session.get(Attachment, attachment_id) is None
