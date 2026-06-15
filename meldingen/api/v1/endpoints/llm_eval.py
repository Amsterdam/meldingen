"""LLM classifier evaluation endpoints.

Runs are persisted in the `llm_eval_run` table and executed in the background
via `asyncio.create_task`, so the HTTP request returns immediately. The caller
polls `GET /runs/{run_id}` for status and results.
"""

import asyncio
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_202_ACCEPTED, HTTP_503_SERVICE_UNAVAILABLE

from meldingen.api.v1 import unauthorized_response
from meldingen.authentication import authenticate_user
from meldingen.database import DatabaseSessionManager
from meldingen.dependencies import classifier_agent, database_session, database_session_manager
from meldingen.models import LlmEvalRun, User
from meldingen.schemas.llm_eval import LlmEvalRunCreateOutput, LlmEvalRunInput
from meldingen.tasks.llm_eval import execute_llm_eval_run

logger = logging.getLogger(__name__)

router = APIRouter()

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
    agent: Annotated[Agent | None, Depends(classifier_agent)],
    session: Annotated[AsyncSession, Depends(database_session)],
    session_manager: Annotated[DatabaseSessionManager, Depends(database_session_manager)],
    user: Annotated[User, Depends(authenticate_user)],
) -> LlmEvalRunCreateOutput:
    if agent is None:
        raise HTTPException(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not enabled. Set API_LLM_ENABLED=true and configure the LLM provider.",
        )

    run = LlmEvalRun()
    run.request_payload = body.model_dump(mode="json")
    run.total = len(body.test_cases)
    run.created_by_user_id = user.id
    session.add(run)
    await session.commit()
    await session.refresh(run)

    asyncio.create_task(execute_llm_eval_run(run.id, body, agent, session_manager))
    logger.info("llm eval run %d: scheduled by user %s", run.id, user.id)

    return LlmEvalRunCreateOutput(run_id=run.id)
