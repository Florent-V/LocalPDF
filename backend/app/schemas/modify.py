from pydantic import BaseModel, Field


class RotateRequest(BaseModel):
    angle: int = Field(ge=90, le=270, multiple_of=90)
    pages: list[int] | None = Field(
        default=None, description="Pages 1-indexées à pivoter. Si absent, toutes."
    )


class WatermarkRequest(BaseModel):
    text: str | None = Field(default=None, description="Texte du filigrane")
    image: bytes | None = Field(default=None, description="Image du filigrane")
    position: str = Field(default="center")
    opacity: float = Field(default=0.3, ge=0.0, le=1.0)
    font_size: int = Field(default=48, ge=8)
    width: int | None = Field(default=None, ge=16)
    pages: list[int] | None = Field(
        default=None, description="Pages 1-indexées ciblées. Si absent, toutes."
    )
