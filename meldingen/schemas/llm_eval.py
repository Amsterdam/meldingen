from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from meldingen.models import LlmEvalRunStatus


class LlmEvalClassificationInput(BaseModel):
    name: str = Field(min_length=1)
    instructions: str | None = Field(default=None)


class LlmEvalTestCaseInput(BaseModel):
    text: str = Field(min_length=1)
    expected: str = Field(min_length=1)


class LlmEvalRunInput(BaseModel):
    classifications: list[LlmEvalClassificationInput] = Field(min_length=1)
    test_cases: list[LlmEvalTestCaseInput] = Field(min_length=1)


class LlmEvalTestCaseResult(BaseModel):
    text: str
    expected: str
    actual: str | None
    passed: bool
    error: str | None = None


class LlmEvalRunCreateOutput(BaseModel):
    run_id: int
    status: Literal[LlmEvalRunStatus.pending] = LlmEvalRunStatus.pending


class LlmEvalRunDetailOutput(BaseModel):
    run_id: int
    status: LlmEvalRunStatus
    request_payload: LlmEvalRunInput
    total: int
    passed: int
    failed: int
    errored: int
    results: list[LlmEvalTestCaseResult]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class LlmEvalRunSummaryOutput(BaseModel):
    run_id: int
    status: LlmEvalRunStatus
    total: int
    passed: int
    failed: int
    errored: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
