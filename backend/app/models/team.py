from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from app.models import BaseDBModel


class TeamRole(str, Enum):
    MANAGER = "manager"
    MEMBER = "member"


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Team(TeamBase, BaseDBModel):
    created_by: UUID
    members_count: Optional[int] = 0
    creator_info: Optional[dict] = None


class TeamMember(BaseModel):
    team_id: UUID
    user_id: UUID
    role: TeamRole = TeamRole.MEMBER
    joined_at: Optional[str] = None
    member_info: Optional[dict] = None
