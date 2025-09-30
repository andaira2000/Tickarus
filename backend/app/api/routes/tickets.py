from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from pydantic import BaseModel
from supabase import AsyncClient

from app.api.dependencies import get_current_user_id, get_supabase_request_client
from app.models.ticket import (
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketList,
    TicketStatus,
    TicketPriority,
)
from app.services.actor_service import ActorService
from app.services.auto_tagging_service import auto_tagging_service
from app.services.metrics_service import MetricsService
from app.services.rootcause_service import rootcause_service
from app.services.similarity_service import similarity_service
from app.services.ticket_service import TicketService

router = APIRouter()


class RatingRequest(BaseModel):
    rating: str


class SimilarTicketsRequest(BaseModel):
    ticket_text: str
    limit: int = 5


class AutoTagRequest(BaseModel):
    title: str
    description: str


class SimilarityClickRequest(BaseModel):
    clicked_ticket_id: UUID
    original_ticket_id: Optional[UUID] = None


@router.post("", response_model=Ticket)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Create a new ticket on behalf of a human user."""
    user_actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )

    return await TicketService.create_ticket(
        ticket_data, user_actor.id, supabase_client
    )


@router.get("", response_model=TicketList)
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    team_id: Optional[UUID] = None,
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    assignee_id: Optional[UUID] = None,
    tag_names: Optional[List[str]] = None,
    commented_by: Optional[UUID] = None,
    search_query: Optional[str] = None,
    created_by_me: Optional[bool] = None,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """List tickets with optional filtering, searching, and pagination."""
    ticket_list = await TicketService.list_tickets(
        page,
        page_size,
        team_id,
        status,
        priority,
        assignee_id,
        tag_names,
        commented_by,
        search_query,
        created_by_me,
        current_user_id,
        supabase_client,
    )

    return TicketList(**ticket_list)


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: UUID, supabase_client: AsyncClient = Depends(get_supabase_request_client)
):
    """Get ticket details by ID."""
    return await TicketService.get_ticket(ticket_id, supabase_client)


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(
    ticket_id: UUID,
    patch: TicketUpdate,
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Update ticket details."""
    return await TicketService.update_ticket(ticket_id, patch, supabase_client)


@router.post("/{ticket_id}/tags")
async def add_tags(
    ticket_id: UUID,
    names: List[str],
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Add tags to a ticket."""
    user_actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )
    await TicketService.add_tags(ticket_id, names, user_actor.id, supabase_client)
    return {"message": "Tags added"}


@router.delete("/{ticket_id}/tags")
async def remove_tags(
    ticket_id: UUID,
    names: List[str],
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Remove tags from a ticket."""
    await TicketService.remove_tags(ticket_id, names, supabase_client)
    return {"message": "Tags removed"}


@router.post("/{ticket_id}/watch")
async def watch_ticket(
    ticket_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Watch a ticket to receive notifications on updates."""
    actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )
    await TicketService.watch(ticket_id, actor.id, supabase_client)
    return {"message": "Now watching ticket"}


@router.delete("/{ticket_id}/watch")
async def unwatch_ticket(
    ticket_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Stop watching a ticket."""
    actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )
    await TicketService.unwatch(ticket_id, actor.id, supabase_client)
    return {"message": "Stopped watching ticket"}


@router.post("/similar")
async def find_similar_tickets(
    request: SimilarTicketsRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Find similar tickets given a ticket title and description."""
    similar_tickets = await similarity_service.find_similar_tickets(
        ticket_text=request.ticket_text, limit=request.limit, user_id=current_user_id
    )

    return similar_tickets


@router.post("/{ticket_id}/ai-analysis/rate")
async def rate_ai_analysis(
    ticket_id: UUID,
    request: RatingRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Rate the quality of AI root cause analysis"""
    await MetricsService.log_event(
        event_type="rootcause_feedback",
        ticket_id=ticket_id,
        user_id=current_user_id,
        ai_feature="current_user_id",
        user_rating=2 if request.rating == "helpful" else 1,
        metadata={"feedback_text": f"User rated analysis as {request.rating}"},
    )

    return {"message": "Rating submitted successfully"}


@router.post("/{ticket_id}/ai-analysis")
async def get_ai_root_cause_analysis(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Get root cause analysis for a ticket using AI."""

    analysis = await rootcause_service.analyze_ticket(
        ticket_id=ticket_id, user_id=current_user_id
    )

    return analysis


@router.post("/auto-tag")
async def get_auto_tagging_suggestions(
    request: AutoTagRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get auto-tagging suggestions for a ticket title and description."""
    suggestions = await auto_tagging_service.auto_tag_ticket(
        request.title, request.description, current_user_id
    )

    return suggestions


@router.post("/similarity-click")
async def log_similarity_click(
    request: SimilarityClickRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Log when user clicks on a similarity suggestion"""
    await MetricsService.log_event(
        event_type="similarity_clicked",
        ticket_id=request.original_ticket_id,
        user_id=current_user_id,
        ai_feature="similarity",
        metadata={"clicked_ticket": str(request.clicked_ticket_id)},
    )

    return {"message": "Click logged successfully"}
