import anthropic
from fastapi import HTTPException

from app.services.ai.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4096,
            )
        except anthropic.APIConnectionError as exc:
            raise HTTPException(
                status_code=503,
                detail="Impossible de contacter le provider Anthropic.",
            ) from exc
        except anthropic.APIStatusError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail="Le provider Anthropic a renvoyé une erreur.",
            ) from exc
        content = response.content
        if content and hasattr(content[0], "text"):
            return content[0].text
        return ""
