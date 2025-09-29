from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id, get_supabase_request_client
from app.models.comment import Comment, CommentCreate, CommentUpdate
from app.services.actor_service import ActorService
from app.services.comment_service import CommentService

router = APIRouter()


@router.post("", response_model=Comment)
async def create_comment(
    payload: CommentCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client=Depends(get_supabase_request_client),
):
    """Create a new comment on a ticket on behalf of a human user."""
    user_actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )

    return await CommentService.create_comment(payload, user_actor.id, supabase_client)


@router.get("/ticket/{ticket_id}", response_model=List[Comment])
async def list_comments(
    ticket_id: UUID, supabase_client=Depends(get_supabase_request_client)
):
    """List comments for a ticket."""
    return await CommentService.list_comments(ticket_id, supabase_client)


@router.patch("/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: UUID,
    patch: CommentUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client=Depends(get_supabase_request_client),
):
    """Update a comment's content on behalf of a human user."""
    user_actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )

    return await CommentService.update_comment(
        comment_id, patch, user_actor.id, supabase_client
    )


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client=Depends(get_supabase_request_client),
):
    """Delete a comment on behalf of a human user"""

    user_actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )

    await CommentService.delete_comment(comment_id, user_actor.id, supabase_client)
    return {"message": "Comment deleted"}
