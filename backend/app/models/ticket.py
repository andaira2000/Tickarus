from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from app.models import BaseDBModel


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketBase(BaseModel):
    team_id: UUID
    title: str = Field(..., min_length=1, max_length=280)
    description: str = Field(..., min_length=1)
    status: Optional[TicketStatus] = TicketStatus.OPEN
    priority: Optional[TicketPriority] = TicketPriority.MEDIUM
    assignee_id: Optional[UUID] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    team_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assignee_id: Optional[UUID] = None


class Ticket(TicketBase, BaseDBModel):
    actor_id: UUID  # Reference to actors table (replaces created_by and created_by_system_user_id)
    updated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    # optional expansions
    tags: Optional[List[str]] = []
    comments_count: Optional[int] = 0
    team_name: Optional[str] = None
    # actor info for display
    creator_info: Optional[dict] = None  # Will be populated with ActorInfo data


class TicketList(BaseModel):
    tickets: List[Ticket]
    total: int
    page: int = 1
    page_size: int = 20
