from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase
from app.models.ticket import (
    TicketCreate,
    TicketUpdate,
    Ticket,
    TicketStatus,
    TicketPriority,
)


class TicketService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_ticket(cls, data: TicketCreate) -> Ticket:
        c = cls._c()
        payload = {
            "team_id": str(data.team_id),
            "title": data.title,
            "description": data.description,
            "status": (
                data.status.value
                if isinstance(data.status, TicketStatus)
                else data.status
            )
            or "open",
            "priority": (
                data.priority.value
                if isinstance(data.priority, TicketPriority)
                else data.priority
            )
            or "medium",
            "assignee_id": str(data.assignee_id) if data.assignee_id else None,
        }
        resp = c.table("tickets").insert(payload).select("*").single().execute()
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Create failed",
            )
        return await cls._hydrate_ticket(resp.data)

    @classmethod
    async def get_ticket(cls, ticket_id: UUID) -> Ticket:
        c = cls._c()
        resp = (
            c.table("tickets").select("*").eq("id", str(ticket_id)).single().execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Ticket not found")
        return await cls._hydrate_ticket(resp.data)

    @classmethod
    async def update_ticket(cls, ticket_id: UUID, patch: TicketUpdate) -> Ticket:
        c = cls._c()
        payload: Dict[str, Any] = {}
        if patch.title is not None:
            payload["title"] = patch.title
        if patch.description is not None:
            payload["description"] = patch.description
        if patch.status is not None:
            payload["status"] = (
                patch.status.value
                if isinstance(patch.status, TicketStatus)
                else patch.status
            )
        if patch.priority is not None:
            payload["priority"] = (
                patch.priority.value
                if isinstance(patch.priority, TicketPriority)
                else patch.priority
            )
        if patch.assignee_id is not None:
            payload["assignee_id"] = (
                str(patch.assignee_id) if patch.assignee_id else None
            )
        if patch.team_id is not None:
            payload["team_id"] = str(patch.team_id)  # reroute

        if not payload:
            return await cls.get_ticket(ticket_id)

        resp = (
            c.table("tickets")
            .update(payload)
            .eq("id", str(ticket_id))
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Update failed",
            )
        return await cls._hydrate_ticket(resp.data)

    @classmethod
    async def list_tickets(
        cls,
        page: int = 1,
        page_size: int = 20,
        team_id: Optional[UUID] = None,
        status_filter: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        assignee_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        tag_names: Optional[List[str]] = None,
        commented_by: Optional[UUID] = None,
        search_query: Optional[str] = None,
    ):
        c = cls._c()
        q = c.table("tickets").select("*", count="exact")

        if team_id:
            q = q.eq("team_id", str(team_id))
        if status_filter:
            q = q.eq(
                "status",
                (
                    status_filter.value
                    if hasattr(status_filter, "value")
                    else status_filter
                ),
            )
        if priority:
            q = q.eq(
                "priority", priority.value if hasattr(priority, "value") else priority
            )
        if assignee_id:
            q = q.eq("assignee_id", str(assignee_id))
        if created_by:
            q = q.eq("created_by", str(created_by))

        # Tags filter (ANY match)
        if tag_names:
            tags_resp = (
                c.table("tags").select("id,name").in_("name", tag_names).execute()
            )
            if tags_resp.error:
                raise HTTPException(
                    http_status.HTTP_400_BAD_REQUEST, tags_resp.error.message
                )
            tag_ids = [t["id"] for t in (tags_resp.data or [])]
            if tag_ids:
                tt_resp = (
                    c.table("ticket_tags")
                    .select("ticket_id")
                    .in_("tag_id", tag_ids)
                    .execute()
                )
                tids = list({row["ticket_id"] for row in (tt_resp.data or [])})
                if tids:
                    q = q.in_("id", tids)
                else:
                    return {
                        "tickets": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                    }
            else:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}

        # Commented by filter
        if commented_by:
            cm_resp = (
                c.table("comments")
                .select("ticket_id")
                .eq("user_id", str(commented_by))
                .execute()
            )
            tids = list({row["ticket_id"] for row in (cm_resp.data or [])})
            if not tids:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}
            q = q.in_("id", tids)

        # Full-text search on generated tsvector (websearch syntax)
        if search_query:
            q = q.text_search(
                "search_tsv", search_query, config="english", type="websearch"
            )

        # Pagination — newest activity first
        from_ = (page - 1) * page_size
        to_ = from_ + (page_size - 1)
        q = q.order("last_activity_at", desc=True).range(from_, to_)

        resp = q.execute()
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)

        data = resp.data or []
        hydrated = [await cls._hydrate_ticket(row) for row in data]
        return {
            "tickets": hydrated,
            "total": resp.count or 0,
            "page": page,
            "page_size": page_size,
        }

    # --------------- tags on a ticket ---------------
    @classmethod
    async def add_tags(cls, ticket_id: UUID, tag_names: List[str]) -> None:
        c = cls._c()
        if not tag_names:
            return
        # ensure tags exist
        for name in tag_names:
            name_l = name.lower()
            tag = c.table("tags").select("id").eq("name", name_l).single().execute()
            tag_id = None
            if tag.data:
                tag_id = tag.data["id"]
            else:
                created = (
                    c.table("tags")
                    .insert({"name": name_l})
                    .select("id")
                    .single()
                    .execute()
                )
                if created.error or not created.data:
                    raise HTTPException(
                        http_status.HTTP_400_BAD_REQUEST,
                        created.error.message if created.error else "Tag create failed",
                    )
                tag_id = created.data["id"]
            # link
            c.table("ticket_tags").insert(
                {"ticket_id": str(ticket_id), "tag_id": tag_id}
            ).execute()

    @classmethod
    async def remove_tags(cls, ticket_id: UUID, tag_names: List[str]) -> None:
        c = cls._c()
        if not tag_names:
            return
        tags_resp = (
            c.table("tags")
            .select("id")
            .in_("name", [n.lower() for n in tag_names])
            .execute()
        )
        ids = [t["id"] for t in (tags_resp.data or [])]
        if ids:
            c.table("ticket_tags").delete().match({"ticket_id": str(ticket_id)}).in_(
                "tag_id", ids
            ).execute()

    # --------------- watchers ---------------
    @classmethod
    async def watch(cls, ticket_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        c.table("ticket_watchers").insert(
            {"ticket_id": str(ticket_id), "user_id": str(user_id)}
        ).execute()

    @classmethod
    async def unwatch(cls, ticket_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        c.table("ticket_watchers").delete().match(
            {"ticket_id": str(ticket_id), "user_id": str(user_id)}
        ).execute()

    # --------------- helpers ---------------
    @classmethod
    async def _hydrate_ticket(cls, row: Dict[str, Any]) -> Ticket:
        c = cls._c()
        tid = row["id"]
        # tags
        ttags = (
            c.table("ticket_tags").select("tags(name)").eq("ticket_id", tid).execute()
        )
        tags = [x["tags"]["name"] for x in (ttags.data or []) if x.get("tags")]
        # comment count
        cc = (
            c.table("comments")
            .select("id", count="exact")
            .eq("ticket_id", tid)
            .execute()
        )
        comments_count = cc.count or 0
        # team name
        team = (
            c.table("teams").select("name").eq("id", row["team_id"]).single().execute()
        )
        team_name = team.data["name"] if team and team.data else None
        row = dict(row)
        row["tags"] = tags
        row["comments_count"] = comments_count
        row["team_name"] = team_name
        return Ticket(**row)
