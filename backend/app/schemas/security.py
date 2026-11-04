from pydantic import BaseModel, Field


class Rectangle(BaseModel):
    page: int = Field(ge=1)
    rect: dict[str, float]


class RedactRequest(BaseModel):
    rectangles: list[Rectangle] | None = None
    terms: list[str] | None = None
