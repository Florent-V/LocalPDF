import openai
from fastapi import HTTPException

from app.services.ai.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.client = openai.AsyncOpenAI(api_key=api_key)

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
                detail="Impossible de contacter le provider OpenAI.",
            ) from exc
        except openai.APIStatusError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail="Le provider OpenAI a renvoyé une erreur.",
            ) from exc
        return response.choices[0].message.content or ""
