from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
    status as http_status,
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


@router.get("/{ticket_id}/similar", response_model=List[Dict[str, Any]])
async def get_similar_tickets(
    ticket_id: UUID,
    limit: int = Query(
        5, ge=1, le=20, description="Number of similar tickets to return"
    ),
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Get tickets similar to the specified ticket"""
    from app.services.similarity_service import similarity_service

    # Get the ticket details first
    ticket = await TicketService.get_ticket(ticket_id, supabase_client)
    if not ticket:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Ticket not found")

    # Combine title and description for similarity search
    ticket_text = f"{ticket.title}. {ticket.description or ''}"

    # Find similar tickets
    similar_tickets = await similarity_service.find_similar_tickets(
        ticket_text=ticket_text,
        current_ticket_id=ticket_id,
        limit=limit,
        user_id=current_user_id,
    )

    return similar_tickets


@router.post("/{ticket_id}/similar/click")
async def log_similarity_click(
    ticket_id: UUID,
    clicked_ticket_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Log when user clicks on a similarity suggestion"""
    from app.services.similarity_service import similarity_service

    await similarity_service.log_similarity_click(
        clicked_ticket_id=clicked_ticket_id,
        original_ticket_id=ticket_id,
        user_id=current_user_id,
    )

    return {"message": "Click logged successfully"}


@router.post("/{ticket_id}/analyze", response_model=Dict[str, Any])
async def analyze_ticket_root_cause(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Perform AI root cause analysis on a ticket"""
    from app.services.rootcause_service import rootcause_service

    analysis = await rootcause_service.analyze_ticket(
        ticket_id=ticket_id, user_id=current_user_id
    )

    return analysis


@router.post("/{ticket_id}/analyze/feedback")
async def submit_analysis_feedback(
    ticket_id: UUID,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1-5"),
    feedback_text: Optional[str] = None,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Submit feedback on root cause analysis quality"""
    from app.services.rootcause_service import rootcause_service

    await rootcause_service.submit_feedback(
        ticket_id=ticket_id,
        user_id=current_user_id,
        rating=rating,
        feedback_text=feedback_text,
    )

    return {"message": "Feedback submitted successfully"}


@router.post("/{ticket_id}/auto-tag", response_model=Dict[str, Any])
async def analyze_ticket_for_tagging(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Analyze ticket for automatic tagging and prioritization suggestions"""
    from app.services.auto_tagging_service import auto_tagging_service

    analysis = await auto_tagging_service.analyze_ticket(
        ticket_id=ticket_id, user_id=current_user_id
    )

    return analysis


@router.post("/{ticket_id}/apply-suggestions")
async def apply_auto_tagging_suggestions(
    ticket_id: UUID,
    apply_tags: List[str] = [],
    apply_priority: bool = False,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Apply automatic tagging and prioritization suggestions"""
    from app.services.auto_tagging_service import auto_tagging_service

    result = await auto_tagging_service.apply_suggestions(
        ticket_id=ticket_id,
        user_id=current_user_id,
        apply_tags=apply_tags,
        apply_priority=apply_priority,
    )

    return result


@router.post("/similar")
async def find_similar_tickets(
    request: SimilarTicketsRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Find similar tickets using semantic similarity"""
    from app.services.similarity_service import similarity_service

    similar_tickets = await similarity_service.find_similar_tickets(
        ticket_text=request.ticket_text, limit=request.limit, user_id=current_user_id
    )

    return similar_tickets


@router.post("/{ticket_id}/ai-analysis")
async def get_ai_root_cause_analysis(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    """Get AI-powered root cause analysis for a ticket"""
    from app.services.rootcause_service import rootcause_service

    analysis = await rootcause_service.analyze_ticket(
        ticket_id=ticket_id, user_id=current_user_id
    )

    return analysis


@router.post("/{ticket_id}/ai-analysis/rate")
async def rate_ai_analysis(
    ticket_id: UUID,
    request: RatingRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Rate the quality of AI root cause analysis"""
    from app.services.rootcause_service import rootcause_service

    await rootcause_service.submit_feedback(
        ticket_id=ticket_id,
        user_id=current_user_id,
        rating=2 if request.rating == "helpful" else 1,  # 2=helpful, 1=not helpful
        feedback_text=f"User rated analysis as {request.rating}",
    )

    return {"message": "Rating submitted successfully"}


@router.post("/auto-tag")
async def get_auto_tagging_suggestions(
    request: AutoTagRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get auto-tagging suggestions for title and description"""
    from app.services.auto_tagging_service import auto_tagging_service

    suggestions = await auto_tagging_service.auto_tag_ticket(
        title=request.title, description=request.description, user_id=current_user_id
    )

    return suggestions


@router.post("/similarity-click")
async def log_similarity_click(
    request: SimilarityClickRequest,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Log when user clicks on a similarity suggestion"""
    from app.services.similarity_service import similarity_service

    await similarity_service.log_similarity_click(
        clicked_ticket_id=request.clicked_ticket_id,
        original_ticket_id=request.original_ticket_id,
        user_id=current_user_id,
    )

    return {"message": "Click logged successfully"}
