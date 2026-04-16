from unittest.mock import MagicMock, patch

from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.providers.openai import OpenAIProvider


def _call_uncached(**setting_overrides: object) -> AzureProvider | OpenAIProvider | None:
    """Call llm_provider_generator without hitting the @lru_cache.

    Imports the underlying function and calls __wrapped__ (the un-decorated
    version) so each test gets a fresh invocation regardless of cache state.
    """
    defaults = {
        "llm_enabled": True,
        "llm_provider": "openai",
        "llm_base_url": "http://localhost:1234",
        "llm_api_key": "",
        "llm_model_identifier": "test-model",
    }
    defaults.update(setting_overrides)

    with patch("meldingen.dependencies.settings", **defaults):
        from meldingen.dependencies import llm_provider_generator

        return llm_provider_generator.__wrapped__()


def test_returns_none_when_llm_disabled() -> None:
    result = _call_uncached(llm_enabled=False)
    assert result is None


def test_returns_openai_provider() -> None:
    result = _call_uncached(llm_provider="openai", llm_base_url="http://localhost:1234")
    assert isinstance(result, OpenAIProvider)


def test_returns_azure_provider_with_api_key() -> None:
    result = _call_uncached(
        llm_provider="azure",
        llm_base_url="https://my-endpoint.openai.azure.com",
        llm_api_key="test-key-123",
    )
    assert isinstance(result, AzureProvider)


@patch("meldingen.dependencies.AsyncAzureOpenAI")
@patch("meldingen.dependencies.get_bearer_token_provider")
@patch("meldingen.dependencies.DefaultAzureCredential")
def test_returns_azure_provider_with_managed_identity(
    mock_credential_cls: MagicMock,
    mock_token_provider_fn: MagicMock,
    mock_openai_cls: MagicMock,
) -> None:
    """When llm_provider is 'azure' and no API key is set, the function should
    use DefaultAzureCredential + get_bearer_token_provider for managed-identity
    token auth instead of an API key."""
    mock_credential = MagicMock()
    mock_credential_cls.return_value = mock_credential
    mock_token_provider = MagicMock()
    mock_token_provider_fn.return_value = mock_token_provider
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client

    with patch(
        "meldingen.dependencies.settings",
        llm_enabled=True,
        llm_provider="azure",
        llm_base_url="https://my-endpoint.openai.azure.com",
        llm_api_key="",
        llm_model_identifier="gpt-4o",
    ):
        from meldingen.dependencies import llm_provider_generator

        result = llm_provider_generator.__wrapped__()

    assert isinstance(result, AzureProvider)

    mock_credential_cls.assert_called_once()
    mock_token_provider_fn.assert_called_once_with(mock_credential, "https://cognitiveservices.azure.com/.default")
    mock_openai_cls.assert_called_once_with(
        azure_endpoint="https://my-endpoint.openai.azure.com",
        azure_ad_token_provider=mock_token_provider,
        api_version="2025-01-01-preview",
    )


def test_returns_none_for_unknown_provider() -> None:
    result = _call_uncached(llm_provider="anthropic")
    assert result is None
