"""Endpoint to run the LLM classifier evaluation suite via the API.

Accepts a set of classifications and test cases in the request body, runs each
test case through the production classifier pipeline, and returns per-case
results with pass/fail status.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import Agent
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from meldingen.adapters.classification.agent_classifier import AgentClassifierAdapter
from meldingen.authentication import authenticate_user
from meldingen.dependencies import classifier_agent
from meldingen.schemas.llm_eval import LlmEvalRunInput, LlmEvalRunOutput, LlmEvalTestCaseResult

logger = logging.getLogger(__name__)

router = APIRouter()


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
        sorting_direction: Any | None = None,
        filters: Any | None = None,
    ) -> list[_FakeClassification]:
        return self._classifications


@router.post("/run", name="llm_eval:run", status_code=HTTP_200_OK, dependencies=[Depends(authenticate_user)])
async def run_llm_eval(
    body: LlmEvalRunInput,
    agent: Annotated[Agent | None, Depends(classifier_agent)],
) -> LlmEvalRunOutput:
    if agent is None:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not enabled. Set API_LLM_ENABLED=true and configure the LLM provider.",
        )

    classifications = [_FakeClassification(name=c.name, instructions=c.instructions) for c in body.classifications]
    repository = _InMemoryClassificationRepository(classifications)
    adapter = AgentClassifierAdapter(agent, repository)  # type: ignore[arg-type]

    results: list[LlmEvalTestCaseResult] = []
    for test_case in body.test_cases:
        try:
            actual = await adapter.classify(test_case.text)
            results.append(
                LlmEvalTestCaseResult(
                    text=test_case.text,
                    expected=test_case.expected,
                    actual=actual,
                    passed=actual == test_case.expected,
                )
            )
        except Exception as exc:
            logger.exception("LLM eval failed for test case: %s", test_case.text[:80])
            results.append(
                LlmEvalTestCaseResult(
                    text=test_case.text,
                    expected=test_case.expected,
                    actual=None,
                    passed=False,
                    error=str(exc),
                )
            )

    passed = sum(1 for r in results if r.passed)
    errored = sum(1 for r in results if r.error is not None)

    return LlmEvalRunOutput(
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        errored=errored,
        results=results,
    )
