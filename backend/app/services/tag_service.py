from typing import List
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase, exec_query, exec_single, first_row
from app.models.tag import Tag, TagCreate


class TagService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_tag(cls, tag_data: TagCreate, actor_id: UUID) -> Tag:
        c = cls._c()
        name = tag_data.name.lower()
        try:
            existing = exec_single(c.table("tags").select("*").eq("name", name))
            return Tag(**existing.data)
        except Exception:
            created = exec_query(
                c.table("tags").insert(
                    {"name": name, "creator_actor_id": str(actor_id)},
                    returning="representation",
                )
            )
            row = first_row(created.data)
            if not row:
                raise HTTPException(
                    http_status.HTTP_400_BAD_REQUEST, "Create tag failed"
                )
            return Tag(**row)

    @classmethod
    async def list_tags(cls) -> List[Tag]:
        c = cls._c()
        resp = exec_query(
            c.table("tags")
            .select("*")
            .order("is_standard", desc=True)
            .order("name", desc=False)
        )
        return [Tag(**r) for r in (resp.data or [])]

    @classmethod
    async def get_popular_tags(cls, limit: int = 10):
        c = cls._c()
        join = exec_query(c.table("ticket_tags").select("tag_id, tags(name)"))
        counts: dict[str, int] = {}
        for row in join.data or []:
            nm = row.get("tags", {}).get("name")
            if nm:
                counts[nm] = counts.get(nm, 0) + 1
        sorted_tags = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_tags]
