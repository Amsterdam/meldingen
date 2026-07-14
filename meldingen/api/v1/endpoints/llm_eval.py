"""LLM classifier evaluation endpoints.

Runs are persisted in the `llm_eval_run` table and executed in the background
via `asyncio.create_task`, so the HTTP request returns immediately. The caller
polls `GET /runs/{run_id}` for status and results.
"""

import asyncio
import logging
from typing import Annotated, Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic_ai import Agent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_202_ACCEPTED,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from meldingen.api.utils import PaginationParams, pagination_params
from meldingen.api.v1 import not_found_response, unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.config import settings
from meldingen.database import DatabaseSessionManager
from meldingen.dependencies import (
    build_model_settings,
    classifier_agent_factory,
    database_session,
    database_session_manager,
)
from meldingen.models import LlmEvalRun, User
from meldingen.schemas.llm_eval import (
    LlmEvalRunCreateOutput,
    LlmEvalRunDetailOutput,
    LlmEvalRunInput,
    LlmEvalRunSummaryOutput,
)
from meldingen.tasks.llm_eval import execute_llm_eval_run

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task[None]] = set()

_service_unavailable_response: dict[str | int, dict[str, Any]] = {
    HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "LLM is not enabled or not configured.",
        "content": {
            "application/json": {
                "example": {"detail": "LLM is not enabled. Set API_LLM_ENABLED=true and configure the LLM provider."},
            }
        },
    }
}


@router.post(
    "/runs",
    name="llm_eval:create_run",
    status_code=HTTP_202_ACCEPTED,
    responses={**unauthorized_response, **_service_unavailable_response},
)
async def create_llm_eval_run(
    body: LlmEvalRunInput,
    build_agent: Annotated[Callable[[str], Agent] | None, Depends(classifier_agent_factory)],
    session: Annotated[AsyncSession, Depends(database_session)],
    session_manager: Annotated[DatabaseSessionManager, Depends(database_session_manager)],
    user: Annotated[User, Depends(authenticate_user)],
) -> LlmEvalRunCreateOutput:
    if build_agent is None:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not enabled. Set API_LLM_ENABLED=true and configure the LLM provider.",
        )

    # A caller may pick the model and reasoning effort per run; anything omitted
    # falls back to the deployment default. An explicit `null` effort (present in
    # the request) means "send no reasoning parameter", so distinguish it from an
    # omitted field via `model_fields_set` before applying the default.
    if body.model is not None and body.model not in settings.llm_model_options:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"model {body.model!r} must be one of {settings.llm_model_options}",
        )

    effort = body.reasoning_effort if "reasoning_effort" in body.model_fields_set else settings.llm_reasoning_effort
    if effort is not None and effort not in settings.llm_reasoning_effort_options:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"reasoning_effort {effort!r} must be one of {settings.llm_reasoning_effort_options}",
        )

    model_identifier = body.model or settings.llm_model_identifier
    # Persist the resolved selection so the stored run records exactly what ran.
    body.model = model_identifier
    body.reasoning_effort = effort

    agent = build_agent(model_identifier)
    model_settings = build_model_settings(model_identifier, effort)

    run = LlmEvalRun()
    run.request_payload = body.model_dump(mode="json")
    run.total = len(body.test_cases)
    run.created_by_user_id = user.id
    session.add(run)
    await session.commit()

    task = asyncio.create_task(execute_llm_eval_run(run.id, body, agent, session_manager, model_settings))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info("llm eval run %d: scheduled by user %s (model=%s, effort=%s)", run.id, user.id, model_identifier, effort)

    return LlmEvalRunCreateOutput(run_id=run.id)


@router.get(
    "/runs/{run_id}",
    name="llm_eval:get_run",
    responses={**unauthorized_response, **not_found_response},
    dependencies=[Depends(authenticate_user)],
)
async def get_llm_eval_run(
    run_id: Annotated[int, Path(description="The run id.", ge=1)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> LlmEvalRunDetailOutput:
    run = await session.get(LlmEvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Not Found")

    request_payload = LlmEvalRunInput.model_validate(run.request_payload)

    return LlmEvalRunDetailOutput(
        run_id=run.id,
        status=run.status,
        model=request_payload.model,
        reasoning_effort=request_payload.reasoning_effort,
        request_payload=request_payload,
        total=run.total,
        passed=run.passed,
        failed=run.failed,
        errored=run.errored,
        results=run.results,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@router.get(
    "/runs",
    name="llm_eval:list_runs",
    responses={**unauthorized_response},
    dependencies=[Depends(authenticate_user)],
)
async def list_llm_eval_runs(
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> list[LlmEvalRunSummaryOutput]:
    limit = pagination["limit"] or 0
    offset = pagination["offset"] or 0

    stmt = select(LlmEvalRun).order_by(LlmEvalRun.id.desc())
    if limit:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)

    result = await session.execute(stmt)
    runs = result.scalars().all()
    return [
        LlmEvalRunSummaryOutput(
            run_id=run.id,
            status=run.status,
            # The summary omits the full request_payload, so surface the run's
            # model and effort (stored inside it) as their own fields.
            model=run.request_payload.get("model"),
            reasoning_effort=run.request_payload.get("reasoning_effort"),
            total=run.total,
            passed=run.passed,
            failed=run.failed,
            errored=run.errored,
            error=run.error,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        for run in runs
    ]
