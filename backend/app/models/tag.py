from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from app.models import BaseDBModel


class Tag(BaseDBModel):
    name: str = Field(..., min_length=1, max_length=64)
    is_standard: bool = False
    creator_actor_id: Optional[UUID] = None  # Reference to actors table (replaces created_by)
    # actor info for display
    creator_info: Optional[dict] = None  # Will be populated with ActorInfo data


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
