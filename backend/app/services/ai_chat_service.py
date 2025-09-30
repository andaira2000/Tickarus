import logging
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.db.database import get_service_client
from app.models.ai_chat import (
    ChatMessage,
    ChatSession,
    ChatSessionCreate,
    ChatMessageCreate,
    ChatRole,
    ChatSessionStatus,
    ChatResponse,
)
from app.services.metrics_service import MetricsService
from app.services.llm_interface import get_llm_service, LLMMessage

logger = logging.getLogger(__name__)


class AIChatService:
    def __init__(self):
        self.max_context_messages = 10
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

    async def create_chat_session(
        self, session_data: ChatSessionCreate, user_id: UUID
    ) -> ChatSession:
        """Create a new chat session for a ticket."""

        supabase_client = get_service_client()
        ticket = (
            await supabase_client.table("tickets")
            .select("id, title, description")
            .eq("id", str(session_data.ticket_id))
            .single()
            .execute()
        ).data

        title = session_data.title or f"AI Chat - {ticket['title'][:50]}..."

        session_payload = {
            "ticket_id": str(session_data.ticket_id),
            "user_id": str(user_id),
            "title": title,
            "status": ChatSessionStatus.ACTIVE.value,
        }

        session = ChatSession(
            **(
                await supabase_client.table("ai_chat_sessions")
                .insert(session_payload, returning="representation")
                .execute()
            ).data[0]
        )

        await self._add_system_message(
            session.id,
            f"Starting AI assistance for ticket: {ticket['title']}\n\nDescription: {ticket['description']}",
        )

        if session_data.initial_message:
            await self.send_message(
                session_id=session.id,
                message_data=ChatMessageCreate(
                    content=session_data.initial_message, role=ChatRole.USER
                ),
                user_id=user_id,
            )

        return session

    async def get_chat_session(self, session_id: UUID, user_id: UUID) -> ChatSession:
        """Get a chat session by ID"""
        supabase_client = get_service_client()

        session = (
            await supabase_client.table("ai_chat_sessions")
            .select("*")
            .eq("id", str(session_id))
            .eq("user_id", str(user_id))
            .single()
            .execute()
        ).data

        return ChatSession(**session)

    async def get_session_messages(
        self, session_id: UUID, user_id: UUID, limit: int = 50
    ) -> List[ChatMessage]:
        """Get messages for a chat session."""

        supabase_client = get_service_client()

        messages = (
            await supabase_client.table("ai_chat_messages")
            .select("*")
            .eq("session_id", str(session_id))
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        ).data

        return [ChatMessage(**msg) for msg in messages]

    async def close_session(self, session_id: UUID, user_id: UUID):
        """Close a chat session"""
        supabase_client = get_service_client()

        await (
            supabase_client.table("ai_chat_sessions")
            .update({"status": ChatSessionStatus.CLOSED.value})
            .eq("id", str(session_id))
            .execute()
        )

    async def get_user_sessions(
        self, user_id: UUID, limit: int = 20
    ) -> List[ChatSession]:
        supabase_client = get_service_client()

        sessions = (
            await supabase_client.table("ai_chat_sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        ).data

        return [ChatSession(**session) for session in sessions]

    async def send_message(
        self, session_id: UUID, message_data: ChatMessageCreate, user_id: UUID
    ) -> ChatResponse:
        """Send a message and get AI response"""

        start_time = time.time()

        session = await self.get_chat_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found or access denied")

        if session.status != ChatSessionStatus.ACTIVE:
            raise ValueError("Cannot send messages to closed session")

        await self._add_message(
            session_id=session_id, role=ChatRole.USER, content=message_data.content
        )

        try:
            ai_response_content, context_used = await self._generate_ai_response(
                session_id=session_id, user_id=user_id
            )

            ai_message = await self._add_message(
                session_id=session_id,
                role=ChatRole.ASSISTANT,
                content=ai_response_content,
                metadata={"context_used": context_used},
            )

            await self._update_session_timestamp(session_id)

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
                    "context_items": len(context_used) if context_used else 0,
                },
                response_time_ms=response_time,
            )

            return ChatResponse(
                message=ai_message, session_updated=True, context_used=context_used
            )

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")

            error_message = await self._add_message(
                session_id=session_id,
                role=ChatRole.ASSISTANT,
                content="I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
            )

            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="ai_chat_error",
                ticket_id=session.ticket_id,
                user_id=user_id,
                ai_feature="chat",
                metadata={"error": str(e)},
                response_time_ms=response_time,
            )

            return ChatResponse(message=error_message, session_updated=True)

    async def _generate_ai_response(
        self, session_id: UUID, user_id: UUID, use_llm: bool = True
    ) -> tuple[str, Dict[str, Any]]:
        messages = await self.get_session_messages(
            session_id, user_id, limit=self.max_context_messages
        )

        session = await self.get_chat_session(session_id, user_id)
        ticket_context = await self._get_ticket_context(session.ticket_id)

        context_used = {
            "ticket_title": ticket_context.get("title"),
            "message_count": len(messages),
            "has_code_context": False,
            "llm_used": False,
        }

        if use_llm:
            try:
                response = await self._llm_generate_response(messages, ticket_context)
                context_used["llm_used"] = True

                return response, context_used
            except Exception as e:
                logger.error(f"LLM response generation failed: {e}. Using fallback.")

        # Fallback logic
        last_user_message = next(
            (msg.content for msg in reversed(messages) if msg.role == ChatRole.USER),
            "Hello",
        )

        if "error" in last_user_message.lower():
            response = "I can help you analyze this error. Can you provide more details about when this error occurs and any relevant log messages?"
        elif "database" in last_user_message.lower():
            response = "For database issues, I'd recommend checking:\n1. Connection pool settings\n2. Query performance and indexes\n3. Network connectivity\n4. Database server logs\n\nCan you share any specific error messages you're seeing?"
        elif "performance" in last_user_message.lower():
            response = "Performance issues can have several causes. Let's start by identifying:\n1. When did you first notice the slowdown?\n2. Is it affecting specific features or the entire application?\n3. Have there been recent deployments?\n\nI can help analyze the bottlenecks once we narrow down the scope."
        else:
            response = f"I understand you're asking about: {last_user_message[:100]}...\n\nBased on the ticket context, I can help you analyze this issue. Could you provide more specific details about what you've already tried?"

        return response, context_used

    async def _llm_generate_response(
        self, messages: List[ChatMessage], ticket_context: Dict[str, Any]
    ) -> str:
        llm_messages = [LLMMessage("system", self.system_prompt)]

        context_parts = [
            f"TICKET CONTEXT:",
            f"Title: {ticket_context.get('title', 'N/A')}",
            f"Description: {ticket_context.get('description', 'N/A')}",
            f"Status: {ticket_context.get('status', 'N/A')}",
            f"Team: {ticket_context.get('team_name', 'N/A')}",
        ]

        if ticket_context.get("recent_comments"):
            context_parts.append("Recent Comments:")
            for comment in ticket_context["recent_comments"]:
                context_parts.append(f"- {comment['content']}...")

        context_message = "\n".join(context_parts)
        llm_messages.append(LLMMessage("system", context_message))

        for msg in messages[-8:]:
            if msg.role != ChatRole.SYSTEM:
                llm_messages.append(LLMMessage(msg.role.value, msg.content))

        llm_service = get_llm_service()
        response = await llm_service.generate_response(
            messages=llm_messages,
        )

        return response

    async def _get_ticket_context(self, ticket_id: UUID) -> Dict[str, Any]:
        supabase_client = get_service_client()

        ticket = (
            await supabase_client.table("tickets")
            .select("id, title, description, status, teams(name)")
            .eq("id", str(ticket_id))
            .single()
            .execute()
        ).data

        comments = (
            await supabase_client.table("comments")
            .select("content, created_at, actors(actor_type)")
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        ).data

        return {
            "id": ticket["id"],
            "title": ticket["title"],
            "description": ticket["description"],
            "status": ticket["status"],
            "team_name": (
                ticket.get("teams", {}).get("name") if ticket.get("teams") else None
            ),
            "recent_comments": comments,
        }

    async def _add_message(
        self,
        session_id: UUID,
        role: ChatRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        supabase_client = get_service_client()

        message_payload = {
            "session_id": str(session_id),
            "role": role.value,
            "content": content,
            "metadata": metadata,
        }

        message = (
            await supabase_client.table("ai_chat_messages")
            .insert(message_payload, returning="representation")
            .execute()
        ).data[0]

        return ChatMessage(**message)

    async def _add_system_message(self, session_id: UUID, content: str) -> ChatMessage:
        return await self._add_message(session_id, ChatRole.SYSTEM, content)

    async def _update_session_timestamp(self, session_id: UUID):
        supabase_client = get_service_client()

        await supabase_client.table("ai_chat_sessions").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(session_id)).execute()


ai_chat_service = AIChatService()
