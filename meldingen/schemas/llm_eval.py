from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from meldingen.config import ReasoningEffort
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
    # The model to evaluate. Omit to use the deployment default
    # (`API_LLM_MODEL_IDENTIFIER`); when set, must be one of `API_LLM_MODEL_OPTIONS`.
    # The endpoint resolves the omitted value and stores the model that actually ran.
    model: str | None = Field(default=None)
    # Reasoning effort for the run. Omit to use the deployment default
    # (`API_LLM_REASONING_EFFORT`); send `null` to send no reasoning parameter at
    # all. Only forwarded to reasoning-capable models (`API_LLM_REASONING_MODELS`).
    reasoning_effort: ReasoningEffort | None = Field(default=None)
    # System prompt for the classifier. Omit to use the deployment default
    # (`API_LLM_CLASSIFICATION_SYSTEM_PROMPT`). The endpoint resolves the omitted
    # value and stores the prompt that actually ran.
    system_prompt: str | None = Field(default=None, min_length=1)


class LlmEvalTestCaseResult(BaseModel):
    text: str
    expected: str
    actual: str | None
    passed: bool
    error: str | None = None


class LlmEvalRunCreateOutput(BaseModel):
    run_id: int
    status: Literal["pending"] = "pending"


class LlmEvalRunDetailOutput(BaseModel):
    run_id: int
    status: LlmEvalRunStatus
    model: str | None
    reasoning_effort: ReasoningEffort | None
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
    model: str | None
    reasoning_effort: ReasoningEffort | None
    total: int
    passed: int
    failed: int
    errored: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
