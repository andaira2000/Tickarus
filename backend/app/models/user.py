from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID


class User(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
