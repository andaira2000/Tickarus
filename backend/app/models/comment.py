from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models import BaseDBModel


class CommentBase(BaseModel):
    ticket_id: UUID
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class Comment(BaseDBModel, CommentBase):
    actor_id: UUID
    is_ai: bool = False
    updated_at: Optional[datetime] = None
    author_info: Optional[dict] = None
