from pydantic import BaseModel, Field
from app.models import BaseDBModel


class Tag(BaseDBModel):
    name: str = Field(..., min_length=1, max_length=64)
    is_standard: bool = False


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
