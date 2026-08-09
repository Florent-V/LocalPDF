from typing import BinaryIO

import pymupdf4llm

from app.services.ai.providers.anthropic_provider import AnthropicProvider
from app.services.ai.providers.base import AIProvider
from app.services.ai.providers.ollama_provider import OllamaProvider
from app.services.ai.providers.openai_provider import OpenAIProvider


def get_provider(provider: str, config: dict) -> AIProvider:
    if provider == "ollama":
        return OllamaProvider(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model", "llama3.1:8b"),
        )
    if provider == "openai":
        return OpenAIProvider(
            api_key=config["api_key"], model=config.get("model", "gpt-4o-mini")
        )
    if provider == "anthropic":
        return AnthropicProvider(
            api_key=config["api_key"],
            model=config.get("model", "claude-3-5-sonnet-20241022"),
        )
    raise ValueError(f"Provider inconnu : {provider}")


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
