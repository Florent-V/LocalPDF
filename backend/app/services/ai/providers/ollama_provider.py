import ipaddress
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.services.ai.providers.base import AIProvider

# Blocks SSRF to link-local addresses (this range covers the AWS/GCP/Azure
# cloud metadata endpoint, 169.254.169.254) while still allowing loopback
# and private-LAN addresses, since pointing at a self-hosted Ollama on the
# user's own network is the whole point of this setting.
_BLOCKED_HOSTNAME_SUFFIXES = ("metadata.google.internal",)


def _validate_ollama_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("URL Ollama invalide.")

    hostname = parsed.hostname
    if hostname.lower() in _BLOCKED_HOSTNAME_SUFFIXES:
        raise ValueError("URL Ollama non autorisée.")

    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if addr.is_link_local or addr.is_multicast or addr.is_unspecified or addr.is_reserved:
        raise ValueError("URL Ollama non autorisée.")


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str):
        super().__init__(model)
        base_url = base_url.rstrip("/")
        _validate_ollama_base_url(base_url)
        self.base_url = base_url

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Impossible de contacter le serveur Ollama configuré.",
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail="Le serveur Ollama configuré a renvoyé une erreur.",
                ) from exc
