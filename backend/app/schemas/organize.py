from pydantic import BaseModel, Field


class SplitRangesRequest(BaseModel):
    ranges: list[tuple[int, int]] | None = Field(
        default=None,
        description="Plages de pages 1-indexées. Si absent, une page par fichier.",
    )


class ReorderRequest(BaseModel):
    new_order: list[int] = Field(
        description="Nouvel ordre des pages, indices 1-indexés."
    )
    rotations: dict[int, int] | None = Field(
        default=None,
        description="Rotation à ajouter par page (indice 1-indexé original) -> delta en degrés.",
    )


class JobResponse(BaseModel):
    job_id: str
    page_count: int
    thumbnails: list[str]


class MergeResponse(BaseModel):
    detail: str


class SplitResponse(BaseModel):
    detail: str
