from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase, exec_query, exec_single, first_row
from app.models.comment import Comment, CommentCreate, CommentUpdate


class CommentService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_comment(cls, payload: CommentCreate, actor_id: UUID) -> Comment:
        c = cls._c()
        resp = exec_query(
            c.table("comments").insert(
                {
                    "ticket_id": str(payload.ticket_id),
                    "actor_id": str(actor_id),
                    "content": payload.content,
                },
                returning="representation",
            )
        )
        row = first_row(resp.data)
        if not row:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Create comment failed"
            )
        return Comment(**row)

    @classmethod
    async def list_comments(cls, ticket_id: UUID) -> List[Comment]:
        c = cls._c()
        resp = exec_query(
            c.table("comments")
            .select("""
                *,
                actors:actor_id(
                    id,
                    actor_type,
                    profiles:profile_id(id, full_name, username, avatar_url),
                    system_users:system_user_id(id, name, type, description)
                )
            """)
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=False)
        )
        
        # Hydrate with actor info
        comments = []
        for comment_data in (resp.data or []):
            if comment_data.get("actors"):
                actor = comment_data["actors"]
                if actor["actor_type"] == "human" and actor.get("profiles"):
                    from ..models.actor import ActorInfo
                    comment_data["author_info"] = ActorInfo.from_human_profile(
                        UUID(actor["id"]), actor["profiles"]
                    ).dict()
                elif actor["actor_type"] == "system" and actor.get("system_users"):
                    from ..models.actor import ActorInfo
                    comment_data["author_info"] = ActorInfo.from_system_user(
                        UUID(actor["id"]), actor["system_users"]
                    ).dict()
            
            # Remove nested actors data
            comment_data.pop("actors", None)
            comments.append(Comment(**comment_data))
            
        return comments

    @classmethod
    async def update_comment(
        cls, comment_id: UUID, patch: CommentUpdate, actor_id: UUID
    ) -> Comment:
        c = cls._c()
        resp = exec_query(
            c.table("comments")
            .update(
                {"content": patch.content, "updated_at": datetime.utcnow().isoformat()},
                returning="representation",
            )
            .eq("id", str(comment_id))
        )
        row = first_row(resp.data)
        if not row:
            exec_single(
                c.table("comments").select("*").eq("id", str(comment_id)),
                not_found_msg="Comment not found",
            )
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Update comment failed"
            )
        return Comment(**row)

    @classmethod
    async def delete_comment(cls, comment_id: UUID, actor_id: UUID) -> None:
        c = cls._c()
        exec_query(c.table("comments").delete().eq("id", str(comment_id)))
