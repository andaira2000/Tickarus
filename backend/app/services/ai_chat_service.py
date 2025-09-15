import time
import json
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from datetime import datetime
from app.db.database import get_supabase, get_service_client, exec_query
from app.models.ai_chat import (
    ChatMessage, ChatSession, ChatSessionCreate, ChatMessageCreate, 
    ChatRole, ChatSessionStatus, ChatResponse
)
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AIChatService:
    """
    AI Chat Assistant Service
    Manages conversations between users and AI for ticket discussions
    """
    
    def __init__(self):
        # Configuration for LLM integration
        self.max_context_messages = 10  # Last N messages for context
        self.max_tokens_per_request = 1000
        self.system_prompt = """You are an expert software engineering assistant helping with ticket analysis and problem-solving.

You have access to:
- The ticket details (title, description, comments)
- Code repository context when relevant
- Historical similar tickets and their resolutions

Your role is to:
1. Help analyze and understand the problem described in the ticket
2. Suggest potential root causes and solutions
3. Provide relevant code examples or configuration fixes
4. Ask clarifying questions when needed
5. Reference similar past issues when helpful

Be concise but thorough. Focus on actionable advice and specific technical solutions."""
    
    @staticmethod
    def _c():
        return get_supabase()
    
    @staticmethod
    def _service_c():
        return get_service_client()
    
    async def create_chat_session(
        self, 
        session_data: ChatSessionCreate, 
        user_id: UUID
    ) -> ChatSession:
        """Create a new chat session for a ticket"""
        
        # Get ticket details for context
        c = self._c()
        ticket_resp = exec_query(
            c.table("tickets")
            .select("id, title, description")
            .eq("id", str(session_data.ticket_id))
            .single()
        )
        
        if not ticket_resp.data:
            raise ValueError("Ticket not found")
        
        ticket = ticket_resp.data
        
        # Auto-generate title if not provided
        title = session_data.title or f"AI Chat - {ticket['title'][:50]}..."
        
        # Create session
        session_payload = {
            "ticket_id": str(session_data.ticket_id),
            "user_id": str(user_id),
            "title": title,
            "status": ChatSessionStatus.ACTIVE.value
        }
        
        session_resp = exec_query(
            c.table("ai_chat_sessions")
            .insert(session_payload, returning="representation")
        )
        
        if not session_resp.data:
            raise Exception("Failed to create chat session")
        
        session = ChatSession(**session_resp.data[0])
        
        # Add initial system message with ticket context
        await self._add_system_message(
            session.id,
            f"Starting AI assistance for ticket: {ticket['title']}\n\nDescription: {ticket['description']}"
        )
        
        # Add initial user message if provided
        if session_data.initial_message:
            await self.send_message(
                session_id=session.id,
                message_data=ChatMessageCreate(
                    content=session_data.initial_message,
                    role=ChatRole.USER
                ),
                user_id=user_id
            )
        
        return session
    
    async def get_chat_session(self, session_id: UUID, user_id: UUID) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        c = self._c()
        
        session_resp = exec_query(
            c.table("ai_chat_sessions")
            .select("*")
            .eq("id", str(session_id))
            .eq("user_id", str(user_id))
            .single()
        )
        
        if not session_resp.data:
            return None
        
        return ChatSession(**session_resp.data)
    
    async def get_session_messages(
        self, 
        session_id: UUID, 
        user_id: UUID,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get messages for a chat session"""
        
        # Verify user has access to session
        session = await self.get_chat_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found or access denied")
        
        c = self._c()
        messages_resp = exec_query(
            c.table("ai_chat_messages")
            .select("*")
            .eq("session_id", str(session_id))
            .order("created_at", desc=False)
            .limit(limit)
        )
        
        return [ChatMessage(**msg) for msg in (messages_resp.data or [])]
    
    async def send_message(
        self, 
        session_id: UUID, 
        message_data: ChatMessageCreate, 
        user_id: UUID
    ) -> ChatResponse:
        """Send a message and get AI response"""
        
        start_time = time.time()
        
        # Verify session access
        session = await self.get_chat_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found or access denied")
        
        if session.status != ChatSessionStatus.ACTIVE:
            raise ValueError("Cannot send messages to closed session")
        
        # Add user message
        user_message = await self._add_message(
            session_id=session_id,
            role=ChatRole.USER,
            content=message_data.content
        )
        
        # Get AI response
        try:
            ai_response_content, context_used = await self._generate_ai_response(
                session_id=session_id,
                user_id=user_id
            )
            
            # Add AI response message
            ai_message = await self._add_message(
                session_id=session_id,
                role=ChatRole.ASSISTANT,
                content=ai_response_content,
                metadata={"context_used": context_used}
            )
            
            # Update session timestamp
            await self._update_session_timestamp(session_id)
            
            # Log metrics
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="ai_chat_message",
                ticket_id=session.ticket_id,
                user_id=user_id,
                ai_feature="chat",
                metadata={
                    "session_id": str(session_id),
                    "message_length": len(message_data.content),
                    "response_length": len(ai_response_content),
                    "context_items": len(context_used) if context_used else 0
                },
                response_time_ms=response_time
            )
            
            return ChatResponse(
                message=ai_message,
                session_updated=True,
                context_used=context_used
            )
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            
            # Add error message
            error_message = await self._add_message(
                session_id=session_id,
                role=ChatRole.ASSISTANT,
                content="I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            )
            
            # Log error metrics
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="ai_chat_error",
                ticket_id=session.ticket_id,
                user_id=user_id,
                ai_feature="chat",
                metadata={"error": str(e)},
                response_time_ms=response_time
            )
            
            return ChatResponse(
                message=error_message,
                session_updated=True
            )
    
    async def _generate_ai_response(
        self, 
        session_id: UUID, 
        user_id: UUID
    ) -> tuple[str, Dict[str, Any]]:
        """Generate AI response (placeholder for LLM integration)"""
        
        # Get recent conversation context
        messages = await self.get_session_messages(session_id, user_id, limit=self.max_context_messages)
        
        # Get ticket context
        session = await self.get_chat_session(session_id, user_id)
        ticket_context = await self._get_ticket_context(session.ticket_id)
        
        # Simulate AI processing delay
        await asyncio.sleep(1)
        
        # For now, return a placeholder response
        # This is where LLM integration would go
        last_user_message = next(
            (msg.content for msg in reversed(messages) if msg.role == ChatRole.USER),
            "Hello"
        )
        
        # Simple response generation (to be replaced with LLM)
        if "error" in last_user_message.lower():
            response = "I can help you analyze this error. Can you provide more details about when this error occurs and any relevant log messages?"
        elif "database" in last_user_message.lower():
            response = "For database issues, I'd recommend checking:\n1. Connection pool settings\n2. Query performance and indexes\n3. Network connectivity\n4. Database server logs\n\nCan you share any specific error messages you're seeing?"
        elif "performance" in last_user_message.lower():
            response = "Performance issues can have several causes. Let's start by identifying:\n1. When did you first notice the slowdown?\n2. Is it affecting specific features or the entire application?\n3. Have there been recent deployments?\n\nI can help analyze the bottlenecks once we narrow down the scope."
        else:
            response = f"I understand you're asking about: {last_user_message[:100]}...\n\nBased on the ticket context, I can help you analyze this issue. Could you provide more specific details about what you've already tried?"
        
        context_used = {
            "ticket_title": ticket_context.get("title"),
            "message_count": len(messages),
            "has_code_context": False  # Would be True with real repo integration
        }
        
        return response, context_used
    
    async def _get_ticket_context(self, ticket_id: UUID) -> Dict[str, Any]:
        """Get ticket details for AI context"""
        c = self._service_c()
        
        ticket_resp = exec_query(
            c.table("tickets")
            .select("id, title, description, status, teams(name)")
            .eq("id", str(ticket_id))
            .single()
        )
        
        if not ticket_resp.data:
            return {}
        
        ticket = ticket_resp.data
        
        # Get recent comments
        comments_resp = exec_query(
            c.table("comments")
            .select("content, created_at, actors(actor_type)")
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=True)
            .limit(5)
        )
        
        return {
            "id": ticket["id"],
            "title": ticket["title"],
            "description": ticket["description"],
            "status": ticket["status"],
            "team_name": ticket.get("teams", {}).get("name") if ticket.get("teams") else None,
            "recent_comments": comments_resp.data or []
        }
    
    async def _add_message(
        self, 
        session_id: UUID, 
        role: ChatRole, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Add a message to the chat session"""
        
        c = self._service_c()
        
        message_payload = {
            "session_id": str(session_id),
            "role": role.value,
            "content": content,
            "metadata": metadata,
            "token_count": int(len(content.split()) * 1.3)  # Rough token estimate
        }
        
        message_resp = exec_query(
            c.table("ai_chat_messages")
            .insert(message_payload, returning="representation")
        )
        
        if not message_resp.data:
            raise Exception("Failed to add message")
        
        return ChatMessage(**message_resp.data[0])
    
    async def _add_system_message(self, session_id: UUID, content: str) -> ChatMessage:
        """Add a system message to the session"""
        return await self._add_message(session_id, ChatRole.SYSTEM, content)
    
    async def _update_session_timestamp(self, session_id: UUID):
        """Update session's updated_at timestamp"""
        c = self._service_c()
        
        exec_query(
            c.table("ai_chat_sessions")
            .update({"updated_at": datetime.utcnow().isoformat()})
            .eq("id", str(session_id))
        )
    
    async def close_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Close a chat session"""
        session = await self.get_chat_session(session_id, user_id)
        if not session:
            return False
        
        c = self._c()
        exec_query(
            c.table("ai_chat_sessions")
            .update({"status": ChatSessionStatus.CLOSED.value})
            .eq("id", str(session_id))
        )
        
        return True
    
    async def get_user_sessions(
        self, 
        user_id: UUID, 
        limit: int = 20
    ) -> List[ChatSession]:
        """Get user's chat sessions"""
        c = self._c()
        
        sessions_resp = exec_query(
            c.table("ai_chat_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .limit(limit)
        )
        
        return [ChatSession(**session) for session in (sessions_resp.data or [])]


# Global instance
ai_chat_service = AIChatService()