from typing import List
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase
from app.models.tag import Tag, TagCreate


class TagService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_tag(cls, tag_data: TagCreate, user_id: UUID) -> Tag:
        c = cls._c()
        name = tag_data.name.lower()
        existing = c.table("tags").select("*").eq("name", name).single().execute()
        if existing and existing.data:
            return Tag(**existing.data)
        resp = (
            c.table("tags")
            .insert({"name": name, "created_by": str(user_id)})
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Create tag failed",
            )
        return Tag(**resp.data)

    @classmethod
    async def list_tags(cls) -> List[Tag]:
        c = cls._c()
        resp = (
            c.table("tags")
            .select("*")
            .order("is_standard", desc=True)
            .order("name", desc=False)
            .execute()
        )
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
        return [Tag(**r) for r in (resp.data or [])]

    @classmethod
    async def get_popular_tags(cls, limit: int = 10):
        c = cls._c()
        # If a SQL function exists, you can use it; otherwise do a simple aggregate
        join = c.table("ticket_tags").select("tag_id, tags(name)").execute()
        counts: dict[str, int] = {}
        for row in join.data or []:
            nm = row.get("tags", {}).get("name")
            if nm:
                counts[nm] = counts.get(nm, 0) + 1
        sorted_tags = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_tags]
