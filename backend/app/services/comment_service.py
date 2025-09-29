from typing import List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status as http_status
from supabase import AsyncClient

from app.models.comment import Comment, CommentCreate, CommentUpdate


class CommentService:
    @staticmethod
    async def create_comment(
        payload: CommentCreate, actor_id: UUID, supabase_client: AsyncClient
    ) -> Comment:
        """Create a new comment on a ticket."""
        comment = (
            await supabase_client.table("comments")
            .insert(
                {
                    "ticket_id": str(payload.ticket_id),
                    "actor_id": str(actor_id),
                    "content": payload.content,
                },
                returning="representation",
            )
            .execute()
        ).data[0]

        return Comment(**comment)

    @staticmethod
    async def list_comments(
        ticket_id: UUID, supabase_client: AsyncClient
    ) -> List[Comment]:
        """List comments for a ticket, with actor info hydrated."""
        comments = (
            await supabase_client.table("comments")
            .select(
                """
                *,
                actors:actor_id(
                    id,
                    actor_type,
                    profiles:profile_id(id, full_name, username, avatar_url),
                    system_users:system_user_id(id, name, type, description)
                )
            """
            )
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=False)
            .execute()
        ).data

        hydrated_comments = []
        for comment in comments:
            if comment.get("actors"):
                actor = comment["actors"]
                if actor["actor_type"] == "human" and actor.get("profiles"):
                    from ..models.actor import ActorInfo

                    comment["author_info"] = ActorInfo.from_human_profile(
                        UUID(actor["id"]), actor["profiles"]
                    ).model_dump()
                elif actor["actor_type"] == "system" and actor.get("system_users"):
                    from ..models.actor import ActorInfo

                    comment["author_info"] = ActorInfo.from_system_user(
                        UUID(actor["id"]), actor["system_users"]
                    ).model_dump()

            comment.pop("actors", None)
            hydrated_comments.append(Comment(**comment))

        return hydrated_comments

    @staticmethod
    async def update_comment(
        comment_id: UUID,
        patch: CommentUpdate,
        actor_id: UUID,
        supabase_client: AsyncClient,
    ) -> Comment:
        """Update a comment's content."""
        existing = (
            await supabase_client.table("comments")
            .select("*")
            .eq("id", str(comment_id))
            .single()
            .execute()
        ).data

        if existing["actor_id"] != str(actor_id):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this comment",
            )

        comment = (
            await supabase_client.table("comments")
            .update(
                {
                    "content": patch.content,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                returning="representation",
            )
            .eq("id", str(comment_id))
            .execute()
        ).data[0]

        return Comment(**comment)

    @staticmethod
    async def delete_comment(
        comment_id: UUID, actor_id: UUID, supabase_client: AsyncClient
    ) -> None:
        """Delete a comment."""
        existing = (
            await supabase_client.table("comments")
            .select("*")
            .eq("id", str(comment_id))
            .single()
            .execute()
        ).data

        if existing["actor_id"] != str(actor_id):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment",
            )

        await supabase_client.table("comments").delete().eq(
            "id", str(comment_id)
        ).execute()
