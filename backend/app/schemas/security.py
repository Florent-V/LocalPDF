from pydantic import BaseModel, Field


class ProtectRequest(BaseModel):
    user_password: str = Field(min_length=1)
    owner_password: str | None = None
    allow_printing: bool = True
    allow_copying: bool = False


class UnlockRequest(BaseModel):
    password: str = Field(min_length=1)


class Rectangle(BaseModel):
    page: int = Field(ge=1)
    rect: dict[str, float]


class RedactRequest(BaseModel):
    rectangles: list[Rectangle] | None = None
    terms: list[str] | None = None


class JobRedactResponse(BaseModel):
    job_id: str
    page_count: int
    thumbnails: list[str]
