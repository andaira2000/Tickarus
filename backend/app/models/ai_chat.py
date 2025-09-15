from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    role: ChatRole = ChatRole.USER


class ChatMessage(BaseModel):
    id: UUID
    session_id: UUID
    role: ChatRole
    content: str
    metadata: Optional[Dict[str, Any]] = None
    token_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    ticket_id: UUID
    title: Optional[str] = Field(None, max_length=200)
    initial_message: Optional[str] = Field(None, min_length=1, max_length=4000)


class ChatSession(BaseModel):
    id: UUID
    ticket_id: UUID
    user_id: UUID
    title: Optional[str] = None
    status: ChatSessionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSession):
    messages: List[ChatMessage] = []


class ChatResponse(BaseModel):
    message: ChatMessage
    session_updated: bool = False
    context_used: Optional[Dict[str, Any]] = None