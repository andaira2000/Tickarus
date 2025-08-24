from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from app.models import BaseDBModel


class Tag(BaseDBModel):
    name: str = Field(..., min_length=1, max_length=64)
    is_standard: bool = False
    created_by: Optional[UUID] = None


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
