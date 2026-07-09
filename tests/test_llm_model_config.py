from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from pydantic_ai.models.openai import OpenAIChatModelSettings

from meldingen.adapters.classification.agent_classifier import AgentClassifierAdapter
from meldingen.config import Settings

# ---------------------------------------------------------------------------
# Config validation: the chosen default must come from the configurable list.
# ---------------------------------------------------------------------------


def test_default_model_must_be_in_options_when_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_enabled=True, llm_model_identifier="does-not-exist")


def test_valid_model_selection_is_accepted() -> None:
    settings = Settings(llm_enabled=True, llm_model_identifier="gpt-4o")
    assert settings.llm_model_identifier == "gpt-4o"


def test_model_not_validated_when_llm_disabled() -> None:
    """Local dev runs the LLM off with a model (e.g. gemma) outside the list."""
    settings = Settings(llm_enabled=False, llm_model_identifier="ai/gemma3:1B-Q4_K_M")
    assert settings.llm_model_identifier == "ai/gemma3:1B-Q4_K_M"


def test_reasoning_effort_must_be_in_options() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_reasoning_effort="high", llm_reasoning_effort_options=["low"])


def test_defaults_are_fast_and_include_standard_options() -> None:
    settings = Settings()
    assert settings.llm_reasoning_effort == "low"
    assert "Mistral-Medium-3.5" in settings.llm_model_options
    assert settings.llm_reasoning_models == ["gpt-5-mini", "gpt-5-nano", "gpt-5.1"]


# ---------------------------------------------------------------------------
# Reasoning mapping: sent natively to reasoning models, omitted otherwise.
# ---------------------------------------------------------------------------


def _mock_settings(**overrides: object) -> MagicMock:
    defaults: dict[str, object] = {
        "llm_model_identifier": "gpt-5-mini",
        "llm_reasoning_models": ["gpt-5-mini", "gpt-5-nano", "gpt-5.1"],
        "llm_reasoning_effort": "low",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


def test_effort_sent_for_reasoning_model() -> None:
    with patch(
        "meldingen.dependencies.settings",
        _mock_settings(llm_model_identifier="gpt-5-mini", llm_reasoning_effort="medium"),
    ):
        from meldingen.dependencies import classification_model_settings

        result = classification_model_settings()

    assert result is not None
    assert result["openai_reasoning_effort"] == "medium"


def test_effort_omitted_for_non_reasoning_model() -> None:
    with patch(
        "meldingen.dependencies.settings", _mock_settings(llm_model_identifier="gpt-4o", llm_reasoning_effort="low")
    ):
        from meldingen.dependencies import classification_model_settings

        assert classification_model_settings() is None


def test_effort_omitted_when_none() -> None:
    with patch(
        "meldingen.dependencies.settings", _mock_settings(llm_model_identifier="gpt-5-mini", llm_reasoning_effort=None)
    ):
        from meldingen.dependencies import classification_model_settings

        assert classification_model_settings() is None


# ---------------------------------------------------------------------------
# Adapter forwards the resolved settings to the model run.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_adapter_forwards_model_settings_to_run() -> None:
    agent = MagicMock()
    run_result = MagicMock()
    run_result.output.classification = "Zwerfvuil"
    agent.run = AsyncMock(return_value=run_result)

    classification = MagicMock()
    classification.name = "Zwerfvuil"
    classification.instructions = None
    repository = MagicMock()
    repository.list = AsyncMock(return_value=[classification])

    model_settings = OpenAIChatModelSettings(openai_reasoning_effort="low")
    adapter = AgentClassifierAdapter(agent, repository, model_settings)

    result = await adapter.classify("er ligt afval op straat")

    assert result == "Zwerfvuil"
    assert agent.run.call_args.kwargs["model_settings"] == model_settings
