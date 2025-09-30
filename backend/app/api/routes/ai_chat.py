from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.dependencies import get_current_user_id
from app.models.ai_chat import (
    ChatSession,
    ChatSessionCreate,
    ChatMessage,
    ChatMessageCreate,
    ChatSessionWithMessages,
    ChatResponse,
)
from app.services.ai_chat_service import ai_chat_service

router = APIRouter()


@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Create a new AI chat session for a ticket."""
    try:
        session = await ai_chat_service.create_chat_session(
            session_data=session_data, user_id=current_user_id
        )
        return session
    except ValueError as e:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(http_status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/sessions", response_model=List[ChatSession])
async def get_user_chat_sessions(
    limit: int = Query(20, ge=1, le=100, description="Number of sessions to return"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get user's chat sessions"""
    sessions = await ai_chat_service.get_user_sessions(
        user_id=current_user_id, limit=limit
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session_with_messages(
    session_id: UUID,
    message_limit: int = Query(
        50, ge=1, le=200, description="Number of messages to return"
    ),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get a chat session with its messages."""
    session = await ai_chat_service.get_chat_session(
        session_id=session_id, user_id=current_user_id
    )

    if not session:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Session not found")

    messages = await ai_chat_service.get_session_messages(
        session_id=session_id, user_id=current_user_id, limit=message_limit
    )

    return ChatSessionWithMessages(**session.model_dump(), messages=messages)


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_chat_message(
    session_id: UUID,
    message_data: ChatMessageCreate,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Send a message to the AI assistent"""
    try:
        response = await ai_chat_service.send_message(
            session_id=session_id, message_data=message_data, user_id=current_user_id
        )
        return response
    except ValueError as e:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(http_status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_chat_messages(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get messages from a chat session"""
    try:
        messages = await ai_chat_service.get_session_messages(
            session_id=session_id, user_id=current_user_id, limit=limit
        )
        return messages
    except ValueError as e:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/sessions/{session_id}/close")
async def close_chat_session(
    session_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Close a chat session"""
    await ai_chat_service.close_session(session_id=session_id, user_id=current_user_id)

    return {"message": "Session closed successfully"}


@router.get("/tickets/{ticket_id}/sessions", response_model=List[ChatSession])
async def get_ticket_chat_sessions(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Get all chat sessions for a specific ticket"""
    all_sessions = await ai_chat_service.get_user_sessions(
        user_id=current_user_id, limit=100
    )

    ticket_sessions = [
        session for session in all_sessions if session.ticket_id == ticket_id
    ]

    return ticket_sessions
