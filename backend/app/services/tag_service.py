import logging
from typing import List
from uuid import UUID

from supabase import AsyncClient

from app.db.database import service_client
from app.models.tag import Tag, TagCreate

logger = logging.getLogger(__name__)


class TagService:
    @staticmethod
    async def create_tag(
        tag_data: TagCreate, actor_id: UUID, supabase_client: AsyncClient
    ) -> Tag:
        """Creates a new tag if it doesn't exist, otherwise returns the existing tag."""
        name = tag_data.name.lower()
        try:
            existing_tag = (
                await supabase_client.table("tags")
                .select("*")
                .eq("name", name)
                .single()
                .execute()
            ).data
            return Tag(**existing_tag)
        except Exception:
            tag = (
                await supabase_client.table("tags")
                .insert(
                    {
                        "name": name,
                        "is_standard": supabase_client == service_client,
                        "creator_actor_id": str(actor_id),
                    },
                    returning="representation",
                )
                .execute()
            ).data[0]

            return Tag(**tag)

    @staticmethod
    async def get_tags_by_names(
        names: List[str], supabase_client: AsyncClient
    ) -> List[Tag]:
        """Get tags by their names."""
        if not names:
            return []

        lower_names = [name.lower() for name in names]
        tags = (
            await supabase_client.table("tags")
            .select("*")
            .in_("name", lower_names)
            .execute()
        ).data

        return [Tag(**tag) for tag in tags]

    @staticmethod
    async def get_all_tags(supabase_client: AsyncClient) -> List[Tag]:
        """Get all tags, standard tags first, then custom tags alphabetically."""
        tags = (
            await supabase_client.table("tags")
            .select("*")
            .order("is_standard", desc=True)
            .order("name", desc=False)
            .execute()
        ).data

        return [Tag(**tag) for tag in tags]

    @staticmethod
    async def get_popular_tags(limit: int, supabase_client: AsyncClient):
        """Get the most popular tags based on their usage in tickets."""
        tags_in_tickets = (
            await supabase_client.table("ticket_tags")
            .select("tag_id, tags(name)")
            .execute()
        ).data

        counts: dict[str, int] = {}
        for tag in tags_in_tickets:
            name = tag.get("tags", {}).get("name")
            if name:
                counts[name] = counts.get(name, 0) + 1
        sorted_tags = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_tags]
