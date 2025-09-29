from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from supabase import AsyncClient

from app.api.dependencies import get_current_user_id, get_supabase_request_client
from app.models.tag import Tag, TagCreate
from app.services.actor_service import ActorService
from app.services.tag_service import TagService

router = APIRouter()


@router.post("", response_model=Tag)
async def create_tag(
    tag: TagCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Create a new tag if it doesn't already exist."""
    actor = await ActorService.get_actor_for_human_user(
        current_user_id, supabase_client
    )
    return await TagService.create_tag(tag, actor.id, supabase_client)


@router.get("", response_model=List[Tag])
async def get_all_tags(
    supabase_client: AsyncClient = Depends(get_supabase_request_client),
):
    """Get all tags."""
    return await TagService.get_all_tags(supabase_client)


@router.get("/popular", response_model=List[dict])
async def get_popular_tags(
    limit: int = 10, supabase_client: AsyncClient = Depends(get_supabase_request_client)
):
    """Get the most popular tags based on their usage in tickets."""
    return await TagService.get_popular_tags(limit, supabase_client)
