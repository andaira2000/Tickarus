from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase, exec_query, exec_single
from app.models.comment import Comment, CommentCreate, CommentUpdate


class CommentService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_comment(cls, payload: CommentCreate, user_id: UUID) -> Comment:
        c = cls._c()
        resp = exec_single(
            c.table("comments")
            .insert(
                {
                    "ticket_id": str(payload.ticket_id),
                    "user_id": str(user_id),
                    "content": payload.content,
                }
            )
            .select("*")
        )
        return Comment(**resp.data)

    @classmethod
    async def list_comments(cls, ticket_id: UUID) -> List[Comment]:
        c = cls._c()
        resp = exec_query(
            c.table("comments")
            .select("*")
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=False)
        )
        return [Comment(**r) for r in (resp.data or [])]

    @classmethod
    async def update_comment(
        cls, comment_id: UUID, patch: CommentUpdate, user_id: UUID
    ) -> Comment:
        c = cls._c()
        resp = exec_single(
            c.table("comments")
            .update(
                {"content": patch.content, "updated_at": datetime.utcnow().isoformat()}
            )
            .eq("id", str(comment_id))
            .select("*"),
            not_found_msg="Comment not found",
        )
        return Comment(**resp.data)

    @classmethod
    async def delete_comment(cls, comment_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        exec_query(c.table("comments").delete().eq("id", str(comment_id)))
