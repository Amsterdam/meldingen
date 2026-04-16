from pydantic import BaseModel, Field


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


class LlmEvalRunOutput(BaseModel):
    total: int
    passed: int
    failed: int
    errored: int
    results: list[LlmEvalTestCaseResult]
