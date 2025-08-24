from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase
from app.models.comment import Comment, CommentCreate, CommentUpdate


class CommentService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_comment(cls, payload: CommentCreate, user_id: UUID) -> Comment:
        c = cls._c()
        resp = (
            c.table("comments")
            .insert(
                {
                    "ticket_id": str(payload.ticket_id),
                    "user_id": str(user_id),
                    "content": payload.content,
                }
            )
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Create failed",
            )
        return Comment(**resp.data)

    @classmethod
    async def list_comments(cls, ticket_id: UUID) -> List[Comment]:
        c = cls._c()
        resp = (
            c.table("comments")
            .select("*")
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=False)
            .execute()
        )
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
        return [Comment(**r) for r in (resp.data or [])]

    @classmethod
    async def update_comment(
        cls, comment_id: UUID, patch: CommentUpdate, user_id: UUID
    ) -> Comment:
        c = cls._c()
        # RLS ensures only owner can update
        resp = (
            c.table("comments")
            .update(
                {"content": patch.content, "updated_at": datetime.utcnow().isoformat()}
            )
            .eq("id", str(comment_id))
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Update failed",
            )
        return Comment(**resp.data)

    @classmethod
    async def delete_comment(cls, comment_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        resp = c.table("comments").delete().eq("id", str(comment_id)).execute()
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
