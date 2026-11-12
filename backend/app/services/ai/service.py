from collections.abc import Callable
from typing import BinaryIO

import pymupdf4llm

from app.services.ai.providers.base import AIProvider
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider


def _require_api_key(config: dict, provider: str) -> str:
    api_key = config.get("api_key")
    if not api_key:
        raise ValueError(f"Une clé API est requise pour le provider « {provider} ».")
    return api_key


def _build_ollama(config: dict) -> AIProvider:
    return OllamaProvider(
        base_url=config.get("base_url", "http://localhost:11434"),
        model=config.get("model", "llama3.1:8b"),
    )


def _openai_compatible(name: str, label: str, default_model: str, default_base_url: str | None):
    """Factory for providers speaking the OpenAI chat-completions protocol."""

    def build(config: dict) -> AIProvider:
        return OpenAIProvider(
            api_key=_require_api_key(config, name),
            model=config.get("model", default_model),
            base_url=config.get("base_url") or default_base_url,
            label=label,
        )

    return build


_PROVIDER_FACTORIES: dict[str, Callable[[dict], AIProvider]] = {
    "ollama": _build_ollama,
    "openai": _openai_compatible("openai", "OpenAI", "gpt-4o-mini", None),
    # Anthropic exposes an OpenAI-compatible endpoint.
    "anthropic": _openai_compatible(
        "anthropic", "Anthropic", "claude-sonnet-4-5", "https://api.anthropic.com/v1/"
    ),
    "openrouter": _openai_compatible(
        "openrouter", "OpenRouter", "openai/gpt-4o-mini", "https://openrouter.ai/api/v1"
    ),
}


def get_provider(provider: str, config: dict) -> AIProvider:
    try:
        factory = _PROVIDER_FACTORIES[provider]
    except KeyError as exc:
        raise ValueError(f"Provider inconnu : {provider}") from exc
    return factory(config)


def pdf_to_markdown(file: BinaryIO) -> str:
    md_text = pymupdf4llm.to_markdown(file)
    return md_text


async def summarize(provider: AIProvider, text: str, language: str = "fr") -> str:
    system = (
        "Tu es un assistant de synthèse de documents. "
        "Résume le texte fourni de manière concise en listant les points clés."
    )
    prompt = f"Résume le texte suivant en {language} :\n\n{text[:12000]}"
    return await provider.complete(system, prompt)


async def translate(provider: AIProvider, text: str, target_language: str) -> str:
    system = "Tu es un traducteur professionnel. Traduis le texte fourni en conservant le format Markdown si présent."
    prompt = f"Traduisez le texte suivant en {target_language} :\n\n{text[:12000]}"
    return await provider.complete(system, prompt)


async def chat_with_pdf(
    provider: AIProvider, text: str, question: str, history: list[dict]
) -> str:
    system = (
        "Tu réponds aux questions sur la base du contenu d'un document PDF fourni. "
        "Si la réponse ne se trouve pas dans le document, dis-le clairement."
    )
    context = f"Contenu du document :\n\n{text[:12000]}\n\nQuestion : {question}"
    return await provider.complete(system, context)
