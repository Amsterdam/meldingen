import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_401_UNAUTHORIZED, HTTP_503_SERVICE_UNAVAILABLE

from meldingen.dependencies import classifier_agent
from meldingen.models import LlmEvalRun, LlmEvalRunStatus, User
from tests.api.v1.endpoints.base import BaseUnauthorizedTest

_VALID_BODY = {
    "classifications": [
        {"name": "Zwerfvuil", "instructions": "Rondslingerend afval"},
        {"name": "Straatverlichting", "instructions": "Kapotte lantaarns"},
    ],
    "test_cases": [
        {"text": "Er ligt rommel op straat", "expected": "Zwerfvuil"},
        {"text": "De lantaarn is kapot", "expected": "Straatverlichting"},
    ],
}


def _agent_returning(value: str, app: FastAPI) -> MagicMock:
    agent = MagicMock()
    out = MagicMock()
    out.classification = value
    agent.run = AsyncMock(return_value=MagicMock(output=out))
    app.dependency_overrides[classifier_agent] = lambda: agent
    return agent


@pytest.fixture
async def persisted_auth_user(db_session: AsyncSession) -> None:
    """Persist a user matching ``authenticate_user_override`` (id=400) so the
    `created_by_user_id` foreign key on `llm_eval_run` resolves."""
    user = User(username="user@example.com", email="user@example.com")
    user.id = 400
    db_session.add(user)
    await db_session.commit()


class TestLlmEvalCreateRunUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "llm_eval:create_run"

    def get_method(self) -> str:
        return "POST"


class TestLlmEvalCreateRunAgentDisabled:
    @pytest.mark.anyio
    async def test_returns_503_when_agent_is_none(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        app.dependency_overrides[classifier_agent] = lambda: None

        response = await client.post(app.url_path_for("llm_eval:create_run"), json=_VALID_BODY)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert "LLM is not enabled" in response.json()["detail"]


class TestLlmEvalCreateRun:
    @pytest.mark.anyio
    async def test_returns_run_id_and_pending(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        persisted_auth_user: None,
        db_session: AsyncSession,
    ) -> None:
        _agent_returning("Zwerfvuil", app)

        response = await client.post(app.url_path_for("llm_eval:create_run"), json=_VALID_BODY)

        assert response.status_code == HTTP_202_ACCEPTED
        body = response.json()
        assert isinstance(body["run_id"], int)
        assert body["status"] == LlmEvalRunStatus.pending.value

        # Drain any pending tasks so they don't leak across tests.
        await asyncio.sleep(0)

    @pytest.mark.anyio
    async def test_creates_row_in_db(
        self,
        app: FastAPI,
        client: AsyncClient,
        auth_user: None,
        persisted_auth_user: None,
        db_session: AsyncSession,
    ) -> None:
        _agent_returning("Zwerfvuil", app)

        response = await client.post(app.url_path_for("llm_eval:create_run"), json=_VALID_BODY)
        run_id = response.json()["run_id"]

        # We do NOT assume the background task has finished — just that the row exists.
        result = await db_session.execute(select(LlmEvalRun).where(LlmEvalRun.id == run_id))
        run = result.scalar_one_or_none()
        assert run is not None
        assert run.total == 2
        assert run.request_payload["classifications"][0]["name"] == "Zwerfvuil"
