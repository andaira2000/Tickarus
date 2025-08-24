from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from app.models import BaseDBModel


class Profile(BaseDBModel):
    id: UUID
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
