import httpx
from fastapi import HTTPException

from app.services.ai.providers.base import AIProvider


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str):
        super().__init__(model)
        self.base_url = base_url.rstrip("/")

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
                    detail=f"Impossible de contacter Ollama : {exc}",
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Erreur Ollama : {exc.response.text}",
                ) from exc
