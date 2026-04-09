"""LLM classifier evaluation suite.

Feeds a fixed set of melding texts through the production classifier setup
(real prompt, real LLM agent, real `AgentClassifierAdapter`) and asserts the
predicted category matches the expected one. Classifications come from
`test_cases.json`, not the database, so the suite is reproducible and
version-controlled.

Run with:

    pytest tests/llm_eval/

These tests are excluded from the default pytest collection (see pyproject.toml).
They are skipped automatically when `API_LLM_ENABLED` is false.

The suite calls `AgentClassifierAdapter.classify()` directly (not `__call__`)
so any LLM/network/parsing exception propagates as a normal pytest failure
instead of being collapsed into a silent `None` return.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic_ai import Agent

from meldingen.adapters.classification.agent_classifier import AgentClassifierAdapter
from meldingen.config import settings
from meldingen.dependencies import classifier_agent, llm_provider_generator
from meldingen.repositories import ClassificationRepository

TEST_DATA_PATH = Path(__file__).parent / "test_cases.json"


def _load_test_data() -> dict[str, Any]:
    with TEST_DATA_PATH.open() as f:
        data: dict[str, Any] = json.load(f)
    return data


_TEST_DATA = _load_test_data()


def _make_classification_mock(name: str, instructions: str | None) -> Mock:
    classification = Mock()
    classification.name = name
    classification.instructions = instructions
    return classification


@pytest.fixture(scope="module")
def fake_classification_repository() -> ClassificationRepository:
    classifications = [
        _make_classification_mock(c["name"], c.get("instructions")) for c in _TEST_DATA["classifications"]
    ]
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(return_value=classifications)
    return repository


# NOTE: function-scoped on purpose. pytest-anyio creates a fresh event loop per
# test function; a module-scoped Agent would carry pooled httpx connections from
# the previous test's (now-closed) loop, causing spurious "Event loop is closed"
# RuntimeErrors and silent openai-python retries on every test after the first.
@pytest.fixture
def llm_agent() -> Agent:
    if not settings.llm_enabled:
        pytest.skip(
            "LLM disabled. Set API_LLM_ENABLED=true and configure API_LLM_PROVIDER, "
            "LLM_URL, LLM_MODEL and (if needed) API_LLM_API_KEY to run this suite."
        )

    provider = llm_provider_generator()
    if provider is None:
        pytest.skip(
            "llm_provider_generator() returned None. Check API_LLM_PROVIDER, LLM_URL "
            "and (for azure) API_LLM_API_KEY."
        )

    agent = classifier_agent(provider)
    if agent is None:
        pytest.skip("classifier_agent() returned None. Check LLM_MODEL and provider settings.")

    return agent


@pytest.fixture
def llm_classifier(
    llm_agent: Agent, fake_classification_repository: ClassificationRepository
) -> AgentClassifierAdapter:
    return AgentClassifierAdapter(llm_agent, fake_classification_repository)


@pytest.mark.llm_eval
@pytest.mark.anyio
@pytest.mark.parametrize(
    "test_case",
    _TEST_DATA["test_cases"],
    ids=[f"{tc['expected']}: {tc['text'][:60]}" for tc in _TEST_DATA["test_cases"]],
)
async def test_llm_classifies_correctly(
    test_case: dict[str, str],
    llm_classifier: AgentClassifierAdapter,
) -> None:
    # Use `classify()` (not `__call__`) so exceptions surface with a real
    # traceback instead of being swallowed into `None` like they are in production.
    actual = await llm_classifier.classify(test_case["text"])

    assert actual == test_case["expected"], (
        "LLM returned the wrong (or no) category.\n"
        f"  Expected: {test_case['expected']!r}\n"
        f"  Actual:   {actual!r}\n"
        f"  Melding:  {test_case['text']!r}"
    )
