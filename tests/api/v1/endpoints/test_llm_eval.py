from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_503_SERVICE_UNAVAILABLE

from meldingen.dependencies import classifier_agent
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


class TestLlmEvalRunUnauthorized(BaseUnauthorizedTest):
    def get_route_name(self) -> str:
        return "llm_eval:run"

    def get_method(self) -> str:
        return "POST"


class TestLlmEvalRunAgentDisabled:
    @pytest.mark.anyio
    async def test_returns_503_when_agent_is_none(self, app: FastAPI, client: AsyncClient, auth_user: None) -> None:
        app.dependency_overrides[classifier_agent] = lambda: None

        response = await client.post(app.url_path_for("llm_eval:run"), json=_VALID_BODY)

        assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
        assert "LLM is not enabled" in response.json()["detail"]


class TestLlmEvalRunSuccess:
    @pytest.fixture
    def mock_agent(self, app: FastAPI) -> MagicMock:
        agent = MagicMock()
        # agent.run() returns a result whose .output has a .classification attr
        mock_output = MagicMock()
        mock_output.classification = "Zwerfvuil"
        mock_result = AsyncMock()
        mock_result.return_value = MagicMock(output=mock_output)
        agent.run = mock_result
        app.dependency_overrides[classifier_agent] = lambda: agent
        return agent

    @pytest.mark.anyio
    async def test_successful_evaluation(
        self, app: FastAPI, client: AsyncClient, auth_user: None, mock_agent: MagicMock
    ) -> None:
        response = await client.post(app.url_path_for("llm_eval:run"), json=_VALID_BODY)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["passed"] + data["failed"] + data["errored"] == data["total"]
        assert len(data["results"]) == 2

        for result in data["results"]:
            assert result["actual"] == "Zwerfvuil"
            assert result["error"] is None

    @pytest.mark.anyio
    async def test_counts_are_consistent(
        self, app: FastAPI, client: AsyncClient, auth_user: None, mock_agent: MagicMock
    ) -> None:
        """Agent always returns 'Zwerfvuil', so first test passes, second fails."""
        response = await client.post(app.url_path_for("llm_eval:run"), json=_VALID_BODY)

        data = response.json()
        assert data["passed"] == 1  # "Zwerfvuil" matches
        assert data["failed"] == 1  # "Straatverlichting" does not match
        assert data["errored"] == 0


class TestLlmEvalRunError:
    @pytest.mark.anyio
    async def test_exception_populates_error_and_increments_errored(
        self, app: FastAPI, client: AsyncClient, auth_user: None
    ) -> None:
        agent = MagicMock()
        agent.run = AsyncMock(side_effect=RuntimeError("LLM exploded"))
        app.dependency_overrides[classifier_agent] = lambda: agent

        response = await client.post(app.url_path_for("llm_eval:run"), json=_VALID_BODY)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["errored"] == 2
        assert data["failed"] == 0
        assert data["passed"] == 0

        for result in data["results"]:
            assert result["passed"] is False
            assert result["actual"] is None
            # Error message should NOT leak internal exception details
            assert result["error"] == "Classification failed for this test case."
