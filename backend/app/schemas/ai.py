from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    provider: str = Field(pattern="^(ollama|openai|anthropic)$")
    base_url: str | None = None
    api_key: str | None = None
    model: str


class SummarizeRequest(BaseModel):
    config: AIConfig
    language: str = "fr"


class TranslateRequest(BaseModel):
    config: AIConfig
    target_language: str = "fr"


class ChatRequest(BaseModel):
    config: AIConfig
    question: str = Field(min_length=1)


class AIJobResponse(BaseModel):
    job_id: str
    page_count: int
    markdown: str
