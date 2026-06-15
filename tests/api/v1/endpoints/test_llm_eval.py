import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_200_OK, HTTP_202_ACCEPTED, HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE

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


class TestLlmEvalGetRunUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "llm_eval:get_run"

    def get_method(self) -> str:
        return "GET"

    def get_path_params(self) -> dict[str, int]:
        return {"run_id": 1}


class TestLlmEvalGetRun:
    @pytest.mark.anyio
    async def test_returns_404_for_unknown_run(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        response = await client.get(app.url_path_for("llm_eval:get_run", run_id=9999999))
        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_returns_full_run_state(
        self, app: FastAPI, client: AsyncClient, auth_user: None, db_session: AsyncSession
    ) -> None:
        run = LlmEvalRun()
        run.status = LlmEvalRunStatus.completed
        run.request_payload = _VALID_BODY
        run.total = 2
        run.passed = 1
        run.failed = 1
        run.results = [
            {"text": "a", "expected": "x", "actual": "x", "passed": True, "error": None},
            {"text": "b", "expected": "y", "actual": "x", "passed": False, "error": None},
        ]
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await client.get(app.url_path_for("llm_eval:get_run", run_id=run.id))
        assert response.status_code == HTTP_200_OK
        body = response.json()
        assert body["run_id"] == run.id
        assert body["status"] == "completed"
        assert body["total"] == 2
        assert body["passed"] == 1
        assert body["failed"] == 1
        assert len(body["results"]) == 2
        assert body["request_payload"]["classifications"][0]["name"] == "Zwerfvuil"
