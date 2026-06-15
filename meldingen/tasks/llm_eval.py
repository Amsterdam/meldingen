"""Background task for running the LLM classifier evaluation suite.

This module owns the long-running work that backs `POST /api/v1/llm-eval/runs`.
The task is scheduled with `asyncio.create_task` from the endpoint and runs
detached for the lifetime of the FastAPI process. Each per-case result is
written to the row immediately so callers polling `GET /runs/{id}` see
progress as it happens.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic_ai import Agent

from meldingen.adapters.classification.agent_classifier import AgentClassifierAdapter
from meldingen.database import DatabaseSessionManager
from meldingen.models import LlmEvalRun, LlmEvalRunStatus
from meldingen.schemas.llm_eval import LlmEvalRunInput, LlmEvalTestCaseResult

logger = logging.getLogger(__name__)

_PER_CASE_ERROR_MESSAGE = "Classification failed for this test case."


@dataclass
class _FakeClassification:
    name: str
    instructions: str | None


class _InMemoryClassificationRepository:
    """Minimal repository backed by the request payload instead of the database."""

    def __init__(self, classifications: Sequence[_FakeClassification]) -> None:
        self._classifications = list(classifications)

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort_attribute_name: str | None = None,
        sort_direction: Any | None = None,
        filters: Any | None = None,
    ) -> list[_FakeClassification]:
        return self._classifications


async def execute_llm_eval_run(
    run_id: int,
    payload: LlmEvalRunInput,
    agent: Agent,
    session_manager: DatabaseSessionManager,
) -> None:
    """Run the LLM eval suite for `run_id`, persisting per-case results as we go."""
    logger.info("llm eval run %d: starting", run_id)

    async with session_manager.session() as session:
        run = await session.get(LlmEvalRun, run_id)
        if run is None:
            logger.warning("llm eval run %d: row missing on start, aborting", run_id)
            return
        run.status = LlmEvalRunStatus.running
        run.started_at = datetime.now()
        await session.commit()

    try:
        classifications = [
            _FakeClassification(name=c.name, instructions=c.instructions) for c in payload.classifications
        ]
        repository = _InMemoryClassificationRepository(classifications)
        adapter = AgentClassifierAdapter(agent, repository)  # type: ignore[arg-type]

        for i, test_case in enumerate(payload.test_cases):
            try:
                actual: str | None = await adapter.classify(test_case.text)
                result = LlmEvalTestCaseResult(
                    text=test_case.text,
                    expected=test_case.expected,
                    actual=actual,
                    passed=actual == test_case.expected,
                )
            except Exception:
                logger.exception("llm eval run %d: test case %d raised", run_id, i)
                result = LlmEvalTestCaseResult(
                    text=test_case.text,
                    expected=test_case.expected,
                    actual=None,
                    passed=False,
                    error=_PER_CASE_ERROR_MESSAGE,
                )

            async with session_manager.session() as session:
                run = await session.get(LlmEvalRun, run_id)
                if run is None:
                    logger.warning("llm eval run %d: row missing mid-run, aborting", run_id)
                    return
                # rebind: in-place .append() is not dirty-tracked on JSON columns
                run.results = [*run.results, result.model_dump(mode="json")]
                if result.error is not None:
                    run.errored += 1
                elif result.passed:
                    run.passed += 1
                else:
                    run.failed += 1
                await session.commit()

        async with session_manager.session() as session:
            run = await session.get(LlmEvalRun, run_id)
            if run is None:
                logger.warning("llm eval run %d: row missing at finalize, aborting", run_id)
                return
            run.status = LlmEvalRunStatus.completed
            run.finished_at = datetime.now()
            await session.commit()

        logger.info("llm eval run %d: completed", run_id)
    except Exception:
        logger.exception("llm eval run %d: failed unexpectedly", run_id)
        async with session_manager.session() as session:
            run = await session.get(LlmEvalRun, run_id)
            if run is None:
                logger.warning("llm eval run %d: row missing at failure, aborting", run_id)
                return
            run.status = LlmEvalRunStatus.failed
            run.error = "Run failed unexpectedly"
            run.finished_at = datetime.now()
            await session.commit()
