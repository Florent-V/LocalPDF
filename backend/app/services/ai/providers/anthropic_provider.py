from anthropic import AsyncAnthropic

from app.services.ai.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.client = AsyncAnthropic(api_key=api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=4096,
        )
        content = response.content
        if content and hasattr(content[0], "text"):
            return content[0].text
        return ""
