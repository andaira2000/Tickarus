from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel

from app.models import BaseDBModel


class ActorType(str, Enum):
    HUMAN = "human"
    SYSTEM = "system"


class ActorBase(BaseModel):
    actor_type: ActorType
    profile_id: Optional[UUID] = None
    system_user_id: Optional[UUID] = None


class Actor(ActorBase, BaseDBModel):
    updated_at: Optional[datetime] = None
    profile: Optional[Dict[str, Any]] = None
    system_user: Optional[Dict[str, Any]] = None


class ActorInfo(BaseModel):
    id: UUID
    actor_type: ActorType
    display_name: str
    avatar_url: Optional[str] = None
    is_system: bool
    system_user_type: Optional[str] = None

    @staticmethod
    def from_human_profile(actor_id: UUID, profile: Dict[str, Any]):
        return ActorInfo(
            id=actor_id,
            actor_type=ActorType.HUMAN,
            display_name=profile.get("full_name")
            or profile.get("username")
            or "Unknown User",
            avatar_url=profile.get("avatar_url"),
            is_system=False,
        )

    @staticmethod
    def from_system_user(actor_id: UUID, system_user: Dict[str, Any]):
        return ActorInfo(
            id=actor_id,
            actor_type=ActorType.SYSTEM,
            display_name=system_user.get("name", "Unknown System User"),
            avatar_url=None,
            is_system=True,
            system_user_type=system_user.get("type"),
        )
