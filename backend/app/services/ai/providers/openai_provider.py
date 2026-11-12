import openai
from fastapi import HTTPException

from app.services.ai.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    """Provider for any OpenAI-compatible API (OpenAI, Anthropic, OpenRouter, vLLM, ...).

    Switching vendor only requires another ``base_url`` / ``api_key`` / ``model``.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        label: str = "OpenAI",
    ):
        super().__init__(model)
        self.label = label
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except openai.APIConnectionError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Impossible de contacter le provider {self.label}.",
            ) from exc
        except openai.APIStatusError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=f"Le provider {self.label} a renvoyé une erreur.",
            ) from exc
        return response.choices[0].message.content or ""
