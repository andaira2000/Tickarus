from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase, exec_query, exec_single, first_row
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
    async def create_ticket(
        cls, data: TicketCreate, actor_id: UUID, client=None
    ) -> Ticket:
        c = client or cls._c()

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
            "actor_id": str(actor_id),
        }
        resp = exec_query(
            c.table("tickets").insert(payload, returning="representation")
        )
        row = first_row(resp.data)
        if not row:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Create ticket failed"
            )

        ticket = await cls._hydrate_ticket(row, client=c)

        # Trigger AI automation for CI-created tickets (fire and forget)
        try:
            from app.services.ai_automation_service import AIAutomationService
            import asyncio

            asyncio.create_task(
                AIAutomationService.handle_ticket_created(ticket.id, actor_id)
            )
        except Exception as e:
            # Don't fail ticket creation if AI automation fails
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"AI automation failed for ticket {ticket.id}: {str(e)}")

        return ticket

    @classmethod
    async def get_ticket(cls, ticket_id: UUID) -> Ticket:
        c = cls._c()
        resp = exec_single(
            c.table("tickets").select("*").eq("id", str(ticket_id)),
            not_found_msg="Ticket not found",
        )
        return await cls._hydrate_ticket(resp.data, client=c)

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
            payload["team_id"] = str(patch.team_id)

        if not payload:
            return await cls.get_ticket(ticket_id)

        resp = exec_query(
            c.table("tickets")
            .update(payload, returning="representation")
            .eq("id", str(ticket_id))
        )
        row = first_row(resp.data)
        if not row:
            exec_single(
                c.table("tickets").select("*").eq("id", str(ticket_id)),
                not_found_msg="Ticket not found",
            )
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Update ticket failed"
            )
        return await cls._hydrate_ticket(row, client=c)

    @classmethod
    async def list_tickets(
        cls,
        page: int = 1,
        page_size: int = 20,
        team_id: Optional[UUID] = None,
        status_filter: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        assignee_id: Optional[UUID] = None,
        tag_names: Optional[List[str]] = None,
        commented_by: Optional[UUID] = None,
        search_query: Optional[str] = None,
        created_by_me: Optional[bool] = None,
        current_user_actor_id: Optional[UUID] = None,
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
        if created_by_me and current_user_actor_id:
            q = q.eq("actor_id", str(current_user_actor_id))

        if tag_names:
            tags_resp = exec_query(
                c.table("tags").select("id,name").in_("name", tag_names)
            )
            tag_ids = [t["id"] for t in (tags_resp.data or [])]
            if tag_ids:
                tt_resp = exec_query(
                    c.table("ticket_tags").select("ticket_id").in_("tag_id", tag_ids)
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

        if commented_by:
            # Need to find tickets where this user (via their actor) has commented
            # First get the user's actor ID
            from ..services.actor_service import ActorService

            user_actor = await ActorService.get_actor_for_user(commented_by)
            if not user_actor:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}

            cm_resp = exec_query(
                c.table("comments")
                .select("ticket_id")
                .eq("actor_id", str(user_actor.id))
            )
            tids = list({row["ticket_id"] for row in (cm_resp.data or [])})
            if not tids:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}
            q = q.in_("id", tids)

        # Apply search before pagination
        if search_query:
            # Use case-insensitive search on title and description
            q = q.or_(f"title.ilike.%{search_query}%,description.ilike.%{search_query}%")

        # Apply ordering and pagination
        q = q.order("last_activity_at", desc=True)

        from_ = (page - 1) * page_size
        to_ = from_ + (page_size - 1)
        q = q.range(from_, to_)

        resp = exec_query(q)
        data = resp.data or []
        hydrated = [await cls._hydrate_ticket(row, client=c) for row in data]
        total = getattr(resp, "count", None) or 0
        return {
            "tickets": hydrated,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @classmethod
    async def add_tags(cls, ticket_id: UUID, tag_names: List[str], client=None) -> None:
        c = client or cls._c()
        if not tag_names:
            return
        for name in tag_names:
            name_l = name.lower()
            # try find
            try:
                existing = exec_single(c.table("tags").select("id").eq("name", name_l))
                tag_id = existing.data["id"]
            except Exception:
                created = exec_query(
                    c.table("tags").insert({"name": name_l}, returning="representation")
                )
                row = first_row(created.data)
                if not row:
                    raise HTTPException(
                        http_status.HTTP_400_BAD_REQUEST,
                        f"Failed to create tag '{name_l}'",
                    )
                tag_id = row["id"]
            exec_query(
                c.table("ticket_tags").upsert(
                    {"ticket_id": str(ticket_id), "tag_id": tag_id},
                    on_conflict="ticket_id,tag_id",
                )
            )

    @classmethod
    async def remove_tags(cls, ticket_id: UUID, tag_names: List[str]) -> None:
        c = cls._c()
        if not tag_names:
            return
        tags_resp = exec_query(
            c.table("tags").select("id").in_("name", [n.lower() for n in tag_names])
        )
        ids = [t["id"] for t in (tags_resp.data or [])]
        if ids:
            exec_query(
                c.table("ticket_tags")
                .delete()
                .eq("ticket_id", str(ticket_id))
                .in_("tag_id", ids)
            )

    @classmethod
    async def watch(cls, ticket_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        exec_query(
            c.table("ticket_watchers").upsert(
                {"ticket_id": str(ticket_id), "user_id": str(user_id)},
                on_conflict="ticket_id,user_id",
            )
        )

    @classmethod
    async def unwatch(cls, ticket_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        exec_query(
            c.table("ticket_watchers")
            .delete()
            .match({"ticket_id": str(ticket_id), "user_id": str(user_id)})
        )

    @classmethod
    async def _hydrate_ticket(cls, row: Dict[str, Any], client=None) -> Ticket:
        c = client or cls._c()
        tid = row["id"]
        ttags = exec_query(
            c.table("ticket_tags").select("tags(name)").eq("ticket_id", tid)
        )
        tags = [x["tags"]["name"] for x in (ttags.data or []) if x.get("tags")]
        cc = exec_query(
            c.table("comments").select("id", count="exact").eq("ticket_id", tid)
        )
        comments_count = getattr(cc, "count", None) or 0
        team = exec_single(c.table("teams").select("name").eq("id", row["team_id"]))
        team_name = team.data["name"]

        # Get creator info from actors
        creator_info = None
        if row.get("actor_id"):
            actor_resp = exec_single(
                c.table("actors")
                .select(
                    "*, profiles(full_name, username, avatar_url), system_users(name, type)"
                )
                .eq("id", row["actor_id"])
            )
            actor_data = actor_resp.data
            if actor_data["actor_type"] == "human" and actor_data.get("profiles"):
                from ..models.actor import ActorInfo

                creator_info = ActorInfo.from_human_profile(
                    UUID(actor_data["id"]), actor_data["profiles"]
                ).dict()
            elif actor_data["actor_type"] == "system" and actor_data.get(
                "system_users"
            ):
                from ..models.actor import ActorInfo

                creator_info = ActorInfo.from_system_user(
                    UUID(actor_data["id"]), actor_data["system_users"]
                ).dict()

        row = dict(row)
        row["tags"] = tags
        row["comments_count"] = comments_count
        row["team_name"] = team_name
        row["creator_info"] = creator_info
        return Ticket(**row)
