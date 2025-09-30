import logging
from uuid import UUID
from datetime import datetime

from app.db.database import get_service_client
from app.models.comment import CommentCreate
from app.services.rootcause_service import rootcause_service
from app.services.comment_service import CommentService

logger = logging.getLogger(__name__)

AI_ASSISTANT_BOT_UUID = "00000000-0000-4000-8000-000000000002"


class AIAutomationService:
    @staticmethod
    async def post_ai_root_cause_analysis(ticket_id: UUID):
        """Post AI root cause analysis as a comment on the ticket"""
        supabase_client = get_service_client()

        logger.info(f"Starting AI root cause analysis for ticket {ticket_id}")

        analysis = await rootcause_service.analyze_ticket(
            ticket_id=ticket_id,
        )

        comment_content = AIAutomationService._format_analysis_comment(analysis)

        comment_payload = CommentCreate(ticket_id=ticket_id, content=comment_content)

        ai_assistant_actor = (
            await supabase_client.table("actors")
            .select("*")
            .eq("system_user_id", AI_ASSISTANT_BOT_UUID)
            .eq("actor_type", "system")
            .single()
            .execute()
        ).data
        ai_assistant_actor_id = UUID(ai_assistant_actor["id"])

        comment = await CommentService.create_comment(
            comment_payload, ai_assistant_actor_id, supabase_client
        )

        logger.info(f"Posted AI analysis comment {comment.id} on ticket {ticket_id}")

    @staticmethod
    def _format_analysis_comment(analysis: dict) -> str:
        """Format the root cause analysis into a readable comment"""

        confidence = analysis.get("confidence_score", 0)
        root_cause = analysis.get("root_cause", "Unable to determine")
        suggestions = analysis.get("suggestions", [])
        similar_tickets = analysis.get("similar_resolved_tickets", [])
        llm_used = analysis.get("llm_used", False)

        if confidence >= 0.8:
            confidence_text = "High"
            confidence_emoji = "🟢"
        elif confidence >= 0.5:
            confidence_text = "Medium"
            confidence_emoji = "🟡"
        else:
            confidence_text = "Low"
            confidence_emoji = "🔴"

        comment = f"""🤖 **AI Root Cause Analysis**

{confidence_emoji} **Confidence Level:** {confidence_text} ({confidence:.1%})

**Root Cause:**
{root_cause}

**Recommended Actions:**"""

        for i, suggestion in enumerate(suggestions, 1):
            comment += f"\n{i}. {suggestion}"

        if similar_tickets:
            comment += f"\n\n**Similar Resolved Issues:**"
            for ticket in similar_tickets[:3]:  # Show max 3
                comment += f"\n- #{ticket['id'][:8]}... - {ticket['title']}"

        method_text = "LLM-powered" if llm_used else "Pattern-based"
        comment += f"\n\n---\n*Analysis method: {method_text} • Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*"

        return comment
