from openai import AsyncOpenAI

from app.services.ai.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
