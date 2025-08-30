from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from app.models import BaseDBModel


class ActorType(str, Enum):
    HUMAN = "human"
    SYSTEM = "system"


class ActorBase(BaseModel):
    actor_type: ActorType
    profile_id: Optional[UUID] = None
    system_user_id: Optional[UUID] = None


class ActorCreate(ActorBase):
    pass


class ActorUpdate(BaseModel):
    actor_type: Optional[ActorType] = None
    profile_id: Optional[UUID] = None
    system_user_id: Optional[UUID] = None


class Actor(ActorBase, BaseDBModel):
    updated_at: Optional[datetime] = None
    
    # Expanded fields for convenience
    profile: Optional[Dict[str, Any]] = None  # Will contain profile data when expanded
    system_user: Optional[Dict[str, Any]] = None  # Will contain system user data when expanded


class ActorInfo(BaseModel):
    """Simplified actor info for display purposes"""
    id: UUID
    actor_type: ActorType
    display_name: str
    avatar_url: Optional[str] = None
    is_system: bool
    system_user_type: Optional[str] = None  # Only present for system actors
    
    @classmethod
    def from_human_profile(cls, actor_id: UUID, profile: Dict[str, Any]):
        return cls(
            id=actor_id,
            actor_type=ActorType.HUMAN,
            display_name=profile.get('full_name') or profile.get('username') or 'Unknown User',
            avatar_url=profile.get('avatar_url'),
            is_system=False
        )
    
    @classmethod
    def from_system_user(cls, actor_id: UUID, system_user: Dict[str, Any]):
        return cls(
            id=actor_id,
            actor_type=ActorType.SYSTEM,
            display_name=system_user.get('name', 'Unknown System User'),
            avatar_url=None,  # System users don't have avatars
            is_system=True,
            system_user_type=system_user.get('type')
        )