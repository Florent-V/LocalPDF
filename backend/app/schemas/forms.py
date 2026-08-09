from pydantic import BaseModel


class FieldInfo(BaseModel):
    name: str
    type: str
    value: str
    options: list[str]


class FillRequest(BaseModel):
    values: dict[str, str]
    flatten: bool = False
