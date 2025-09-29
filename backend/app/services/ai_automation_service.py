import asyncio
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.db.database import get_service_client, exec_query
from app.services.rootcause_service import rootcause_service
from app.services.comment_service import CommentService
from app.services.actor_service import ActorService

logger = logging.getLogger(__name__)


class AIAutomationService:
    """
    Handles automated AI responses and integrations
    """

    # System user UUIDs
    CI_AUTOMATION_BOT_UUID = "00000000-0000-4000-8000-000000000001"
    AI_ASSISTANT_BOT_UUID = "00000000-0000-4000-8000-000000000002"

    @classmethod
    async def handle_ticket_created(cls, ticket_id: UUID, creator_actor_id: UUID):
        """
        Handle ticket creation events - trigger AI analysis for CI-created tickets

        Args:
            ticket_id: ID of the newly created ticket
            creator_actor_id: Actor ID of who created the ticket
        """
        try:
            # Check if ticket was created by CI Automation Bot
            if await cls._is_ci_automation_ticket(creator_actor_id):
                logger.info(f"CI ticket detected: {ticket_id}, triggering AI analysis")

                # Trigger AI root cause analysis with a small delay to ensure ticket is fully created
                await asyncio.sleep(2)
                await cls._post_ai_root_cause_analysis(ticket_id)

        except Exception as e:
            logger.error(f"Error in AI automation for ticket {ticket_id}: {str(e)}")

    @classmethod
    async def _is_ci_automation_ticket(cls, creator_actor_id: UUID) -> bool:
        """Check if the ticket was created by CI Automation Bot"""
        try:
            c = get_service_client()

            # Get actor details
            actor_resp = exec_query(
                c.table("actors")
                .select("system_user_id, actor_type")
                .eq("id", str(creator_actor_id))
                .single()
            )

            if not actor_resp.data:
                return False

            actor = actor_resp.data

            # Check if it's a system actor with CI automation system user
            if (
                actor.get("actor_type") == "system"
                and actor.get("system_user_id") == cls.CI_AUTOMATION_BOT_UUID
            ):
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking if CI automation ticket: {str(e)}")
            return False

    @classmethod
    async def _post_ai_root_cause_analysis(cls, ticket_id: UUID):
        """Post AI root cause analysis as a comment on the ticket"""
        try:
            c = get_service_client()

            # Get AI Assistant bot actor - use simpler query to avoid 406 error
            try:
                ai_assistant_resp = exec_query(
                    c.table("actors")
                    .select("*")
                    .eq("system_user_id", cls.AI_ASSISTANT_BOT_UUID)
                    .eq("actor_type", "system")
                    .single()
                )

                if not ai_assistant_resp.data:
                    logger.error("AI Assistant actor not found")
                    return

                ai_assistant_actor_id = UUID(ai_assistant_resp.data["id"])
                logger.info(f"Found AI Assistant actor: {ai_assistant_actor_id}")

            except Exception as e:
                logger.error(f"Error finding AI Assistant actor: {str(e)}")
                return

            # Perform root cause analysis
            logger.info(f"Starting AI root cause analysis for ticket {ticket_id}")
            analysis = await rootcause_service.analyze_ticket(
                ticket_id=ticket_id,
                user_id=None,
                client=c,  # System operation with service client
            )

            # Format analysis as a comment
            comment_content = cls._format_analysis_comment(analysis)

            # Post comment as AI Assistant
            from app.models.comment import CommentCreate

            comment_payload = CommentCreate(
                ticket_id=ticket_id, content=comment_content
            )

            comment = await CommentService.create_comment(
                payload=comment_payload, actor_id=ai_assistant_actor_id, client=c
            )

            logger.info(
                f"Posted AI analysis comment {comment.id} on ticket {ticket_id}"
            )

        except Exception as e:
            logger.error(
                f"Error posting AI root cause analysis for ticket {ticket_id}: {str(e)}"
            )

    @classmethod
    def _format_analysis_comment(cls, analysis: dict) -> str:
        """Format the root cause analysis into a readable comment"""

        confidence = analysis.get("confidence_score", 0)
        root_cause = analysis.get("root_cause", "Unable to determine")
        suggestions = analysis.get("suggestions", [])
        similar_tickets = analysis.get("similar_resolved_tickets", [])
        analysis_method = analysis.get("analysis_method", "unknown")
        llm_used = analysis.get("llm_used", False)

        # Format confidence level
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

        # Add analysis metadata
        method_text = "LLM-powered" if llm_used else "Pattern-based"
        comment += f"\n\n---\n*Analysis method: {method_text} • Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*"

        return comment

    @classmethod
    async def trigger_manual_analysis(
        cls, ticket_id: UUID, user_id: Optional[UUID] = None
    ) -> bool:
        """
        Manually trigger AI analysis for any ticket

        Args:
            ticket_id: ID of ticket to analyze
            user_id: User requesting the analysis (for metrics)

        Returns:
            True if analysis was posted successfully
        """
        try:
            await cls._post_ai_root_cause_analysis(ticket_id)
            return True
        except Exception as e:
            logger.error(
                f"Error in manual AI analysis for ticket {ticket_id}: {str(e)}"
            )
            return False


# Global instance
ai_automation_service = AIAutomationService()
