from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from typing import Optional, List, Dict, Any
from uuid import UUID
from app.api.dependencies import get_current_user_id
from app.models.ticket import (
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketList,
    TicketStatus,
    TicketPriority,
)
from app.services.ticket_service import TicketService

router = APIRouter()


@router.post("/", response_model=Ticket)
async def create_ticket(
    ticket: TicketCreate, current_user_id: UUID = Depends(get_current_user_id)
):
    # Get the actor ID for the current user
    from app.services.actor_service import ActorService
    user_actor = await ActorService.get_actor_for_user(current_user_id)
    if not user_actor:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST, 
            "User actor not found"
        )
    
    return await TicketService.create_ticket(ticket, user_actor.id)


@router.get("/", response_model=TicketList)
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    team_id: Optional[UUID] = None,
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    assignee_id: Optional[UUID] = None,
    tags: Optional[List[str]] = Query(
        None, description="Filter by tag names (any match)"
    ),
    commented_by: Optional[UUID] = None,
    q: Optional[str] = Query(None, description="Keyword search"),
    created_by_me: Optional[bool] = None,
    current_user_id: UUID = Depends(get_current_user_id),
):
    # Get current user's actor ID if needed for created_by_me filter
    current_user_actor_id = None
    if created_by_me:
        from app.services.actor_service import ActorService
        user_actor = await ActorService.get_actor_for_user(current_user_id)
        if user_actor:
            current_user_actor_id = user_actor.id
    
    result = await TicketService.list_tickets(
        page=page,
        page_size=page_size,
        team_id=team_id,
        status_filter=status,
        priority=priority,
        assignee_id=assignee_id,
        tag_names=tags,
        commented_by=commented_by,
        search_query=q,
        created_by_me=created_by_me,
        current_user_actor_id=current_user_actor_id,
    )
    return TicketList(**result)


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    return await TicketService.get_ticket(ticket_id)


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(
    ticket_id: UUID,
    patch: TicketUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
):
    return await TicketService.update_ticket(ticket_id, patch)


# Tag management on a ticket
@router.post("/{ticket_id}/tags")
async def add_tags(
    ticket_id: UUID,
    names: List[str],
    current_user_id: UUID = Depends(get_current_user_id),
):
    await TicketService.add_tags(ticket_id, names)
    return {"message": "Tags added"}


@router.delete("/{ticket_id}/tags")
async def remove_tags(
    ticket_id: UUID,
    names: List[str],
    current_user_id: UUID = Depends(get_current_user_id),
):
    await TicketService.remove_tags(ticket_id, names)
    return {"message": "Tags removed"}


# Watch / Unwatch
@router.post("/{ticket_id}/watch")
async def watch_ticket(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    await TicketService.watch(ticket_id, current_user_id)
    return {"message": "Now watching ticket"}


@router.delete("/{ticket_id}/watch")
async def unwatch_ticket(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    await TicketService.unwatch(ticket_id, current_user_id)
    return {"message": "Stopped watching ticket"}
