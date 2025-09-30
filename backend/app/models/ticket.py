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
    status: TicketStatus
    priority: TicketPriority
    assignee_id: Optional[UUID]


class TicketCreate(BaseModel):
    team_id: UUID
    title: str = Field(..., min_length=1, max_length=280)
    description: str = Field(..., min_length=1)
    priority: TicketPriority
    assignee_id: Optional[UUID] = None


class TicketUpdate(BaseModel):
    team_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assignee_id: Optional[UUID] = None


class Ticket(TicketBase, BaseDBModel):
    actor_id: UUID
    updated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    tags: Optional[List[str]] = []
    comment_count: Optional[int] = 0
    team_name: Optional[str] = None
    creator_info: Optional[dict] = None


class TicketList(BaseModel):
    tickets: List[Ticket]
    total: int
    page: int = 1
    page_size: int = 20
