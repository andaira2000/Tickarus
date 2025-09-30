import logging
from typing import List, Optional
from uuid import UUID

import asyncio
from supabase import AsyncClient

from app.models.actor import ActorInfo
from app.models.tag import TagCreate
from app.models.ticket import (
    TicketCreate,
    TicketUpdate,
    Ticket,
    TicketStatus,
    TicketPriority,
)

from app.services.actor_service import ActorService
from app.services.tag_service import TagService


logger = logging.getLogger(__name__)


class TicketService:
    @staticmethod
    async def create_ticket(
        ticket_data: TicketCreate, actor_id: UUID, supabase_client: AsyncClient
    ) -> Ticket:
        """Create a new ticket."""
        payload = {
            "team_id": str(ticket_data.team_id),
            "title": ticket_data.title,
            "description": ticket_data.description,
            "status": "open",
            "priority": ticket_data.priority.value,
            "assignee_id": (
                str(ticket_data.assignee_id) if ticket_data.assignee_id else None
            ),
            "actor_id": str(actor_id),
        }

        ticket = Ticket(
            **(
                await supabase_client.table("tickets")
                .insert(payload, returning="representation")
                .execute()
            ).data[0]
        )

        ticket = await TicketService._hydrate_ticket(ticket, supabase_client)

        return ticket

    @staticmethod
    async def get_ticket(ticket_id: UUID, supabase_client: AsyncClient) -> Ticket:
        ticket = Ticket(
            **(
                await supabase_client.table("tickets")
                .select("*")
                .eq("id", str(ticket_id))
                .single()
                .execute()
            ).data
        )

        return await TicketService._hydrate_ticket(ticket, supabase_client)

    @staticmethod
    async def update_ticket(
        ticket_id: UUID, patch: TicketUpdate, supabase_client: AsyncClient
    ) -> Ticket:
        payload = patch.model_dump(exclude_unset=True, exclude_none=True)

        if not payload:
            return await TicketService.get_ticket(ticket_id, supabase_client)

        ticket = Ticket(
            **(
                await supabase_client.table("tickets")
                .update(payload, returning="representation")
                .eq("id", str(ticket_id))
                .execute()
            ).data[0]
        )

        return await TicketService._hydrate_ticket(ticket, supabase_client)

    @staticmethod
    async def list_tickets(
        page: int,
        page_size: int,
        team_id: Optional[UUID],
        status: Optional[TicketStatus],
        priority: Optional[TicketPriority],
        assignee_id: Optional[UUID],
        tag_names: Optional[List[str]],
        commented_by: Optional[UUID],
        search_query: Optional[str],
        created_by_me: Optional[bool],
        current_user_id: UUID,
        supabase_client: AsyncClient,
    ):
        """List tickets with optional filtering, searching, and pagination."""
        query = supabase_client.table("tickets").select("*", count="exact")

        if team_id:
            query = query.eq("team_id", str(team_id))

        if status:
            query = query.eq("status", status.value)

        if priority:
            query = query.eq("priority", priority.value)

        if assignee_id:
            query = query.eq("assignee_id", str(assignee_id))

        if created_by_me:
            user_actor = await ActorService.get_actor_for_human_user(
                current_user_id, supabase_client
            )
            query = query.eq("actor_id", str(user_actor.id))

        if tag_names:
            tags = await TagService.get_tags_by_names(tag_names, supabase_client)
            tag_ids = [tag.id for tag in tags]

            if not tag_ids:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}

            tickets_with_tags = (
                await supabase_client.table("ticket_tags")
                .select("ticket_id")
                .in_("tag_id", tag_ids)
                .execute()
            ).data
            ticket_ids = list({ticket["ticket_id"] for ticket in tickets_with_tags})

            if not ticket_ids:
                return {
                    "tickets": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                }

            query = query.in_("id", ticket_ids)

        if commented_by:
            user_actor = await ActorService.get_actor_for_human_user(
                commented_by, supabase_client
            )
            if not user_actor:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}

            comments = (
                await supabase_client.table("comments")
                .select("ticket_id")
                .eq("actor_id", str(user_actor.id))
                .execute()
            ).data

            ticket_ids = list({comment["ticket_id"] for comment in comments})
            if not ticket_ids:
                return {"tickets": [], "total": 0, "page": page, "page_size": page_size}
            query = query.in_("id", ticket_ids)

        query = query.order("last_activity_at", desc=True)

        # Apply search and pagination
        offset = (page - 1) * page_size
        if search_query:
            query = query.text_search(
                "search_tsv", f"'{search_query}'", options={"config": "english"}
            )
            query.params = query.params.add("limit", str(page_size)).add(
                "offset", str(offset)
            )
        else:
            query = query.limit(page_size).offset(offset)

        result = await query.execute()
        tickets = result.data
        total_count = result.count

        hydrated_tickets = await asyncio.gather(
            *[
                TicketService._hydrate_ticket(Ticket(**ticket), supabase_client)
                for ticket in tickets
            ]
        )

        return {
            "tickets": hydrated_tickets,
            "total": total_count,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def add_tags(
        ticket_id: UUID,
        tag_names: List[str],
        actor_id: UUID,
        supabase_client: AsyncClient,
    ) -> None:
        """Add tags to a ticket, creating any tags that don't already exist."""
        if not tag_names:
            return

        for name in tag_names:
            tag = await TagService.create_tag(
                TagCreate(name=name), actor_id, supabase_client
            )
            await supabase_client.table("ticket_tags").upsert(
                {"ticket_id": str(ticket_id), "tag_id": str(tag.id)},
                on_conflict="ticket_id,tag_id",
                ignore_duplicates=True,
            ).execute()

    @staticmethod
    async def remove_tags(
        ticket_id: UUID, tag_names: List[str], supabase_client: AsyncClient
    ) -> None:
        """Remove tags from a ticket."""
        if not tag_names:
            return

        tags = (
            await supabase_client.table("tags")
            .select("id")
            .in_("name", [n.lower() for n in tag_names])
            .execute()
        ).data
        ids = [tag["id"] for tag in tags]

        if ids:
            (
                await supabase_client.table("ticket_tags")
                .delete()
                .eq("ticket_id", str(ticket_id))
                .in_("tag_id", ids)
                .execute()
            )

    @staticmethod
    async def watch(
        ticket_id: UUID, actor_id: UUID, supabase_client: AsyncClient
    ) -> None:
        """Add a watcher to a ticket."""
        await supabase_client.table("ticket_watchers").upsert(
            {"ticket_id": str(ticket_id), "actor_id": str(actor_id)},
            on_conflict="ticket_id,actor_id",
            ignore_duplicates=True,
        ).execute()

    @staticmethod
    async def unwatch(
        ticket_id: UUID, actor_id: UUID, supabase_client: AsyncClient
    ) -> None:
        """Remove a watcher from a ticket."""
        await supabase_client.table("ticket_watchers").delete().match(
            {"ticket_id": str(ticket_id), "actor_id": str(actor_id)}
        ).execute()

    @staticmethod
    async def _hydrate_ticket(ticket: Ticket, supabase_client: AsyncClient) -> Ticket:
        """Given a ticket row from the DB, populate related fields and return Ticket model."""
        ticket_id = ticket.id

        ticket_tags = (
            await supabase_client.table("ticket_tags")
            .select("tags(name)")
            .eq("ticket_id", ticket_id)
            .execute()
        ).data

        tag_names = [tag["tags"]["name"] for tag in ticket_tags if tag.get("tags")]

        comment_count = (
            await supabase_client.table("comments")
            .select("id", count="exact", head=True)
            .eq("ticket_id", ticket_id)
            .execute()
        ).count

        team_name = (
            await supabase_client.table("teams")
            .select("name")
            .eq("id", ticket.team_id)
            .single()
            .execute()
        ).data["name"]

        creator_info = None

        actor = (
            await supabase_client.table("actors")
            .select(
                "*, profiles(full_name, username, avatar_url), system_users(name, type)"
            )
            .eq("id", ticket.actor_id)
            .single()
            .execute()
        ).data

        if actor["actor_type"] == "human" and actor.get("profiles"):
            creator_info = ActorInfo.from_human_profile(
                UUID(actor["id"]), actor["profiles"]
            ).model_dump()
        elif actor["actor_type"] == "system" and actor.get("system_users"):
            creator_info = ActorInfo.from_system_user(
                UUID(actor["id"]), actor["system_users"]
            ).model_dump()

        hydrated_ticket = dict(ticket)

        hydrated_ticket["tags"] = tag_names
        hydrated_ticket["comment_count"] = comment_count
        hydrated_ticket["team_name"] = team_name
        hydrated_ticket["creator_info"] = creator_info

        return Ticket(**hydrated_ticket)
