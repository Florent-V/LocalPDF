import pytest

from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.service import get_provider


def test_get_provider_returns_ollama():
    provider = get_provider("ollama", {})
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3.1:8b"


def test_get_provider_returns_openai():
    provider = get_provider("openai", {"api_key": "sk-test"})
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_returns_anthropic():
    provider = get_provider("anthropic", {"api_key": "sk-test"})
    assert isinstance(provider, OpenAIProvider)
    assert str(provider.client.base_url) == "https://api.anthropic.com/v1/"


def test_get_provider_openrouter_and_custom_base_url():
    default = get_provider("openrouter", {"api_key": "k"})
    assert str(default.client.base_url) == "https://openrouter.ai/api/v1/"
    custom = get_provider("openai", {"api_key": "k", "base_url": "http://vllm:8000/v1"})
    assert str(custom.client.base_url) == "http://vllm:8000/v1/"


def test_get_provider_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_provider("does-not-exist", {})


def test_get_provider_openai_without_api_key_raises_value_error():
    """A missing api_key must surface as a clean ValueError (mapped to a
    400 by the router), not an unhandled KeyError producing a 500."""
    with pytest.raises(ValueError):
        get_provider("openai", {})


def test_get_provider_anthropic_without_api_key_raises_value_error():
    with pytest.raises(ValueError):
        get_provider("anthropic", {})
