from pydantic import BaseModel, Field


class PdfToImagesRequest(BaseModel):
    dpi: int = Field(default=150, ge=72, le=600)
    fmt: str = Field(default="png", pattern="^(png|jpg|jpeg|webp)$")
