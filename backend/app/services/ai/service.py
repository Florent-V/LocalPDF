from collections.abc import Callable
from typing import BinaryIO

import pymupdf4llm

from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.base import AIProvider
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.openrouter_provider import OpenRouterProvider


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


def _build_openai(config: dict) -> AIProvider:
    return OpenAIProvider(
        api_key=_require_api_key(config, "openai"),
        model=config.get("model", "gpt-4o-mini"),
    )


def _build_anthropic(config: dict) -> AIProvider:
    return AnthropicProvider(
        api_key=_require_api_key(config, "anthropic"),
        model=config.get("model", "claude-3-5-sonnet-20241022"),
    )


def _build_openrouter(config: dict) -> AIProvider:
    return OpenRouterProvider(
        api_key=_require_api_key(config, "openrouter"),
        model=config.get("model", "openai/gpt-4o-mini"),
        base_url=config.get("base_url") or None,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[dict], AIProvider]] = {
    "ollama": _build_ollama,
    "openai": _build_openai,
    "anthropic": _build_anthropic,
    "openrouter": _build_openrouter,
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
