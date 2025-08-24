from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from app.api.dependencies import get_current_user_id
from app.models.tag import Tag, TagCreate
from app.services.tag_service import TagService

router = APIRouter()


@router.post("/", response_model=Tag)
async def create_tag(
    tag: TagCreate, current_user_id: UUID = Depends(get_current_user_id)
):
    return await TagService.create_tag(tag, current_user_id)


@router.get("/", response_model=List[Tag])
async def list_tags(current_user_id: UUID = Depends(get_current_user_id)):
    return await TagService.list_tags()


@router.get("/popular", response_model=List[dict])
async def get_popular_tags(
    limit: int = 10, current_user_id: UUID = Depends(get_current_user_id)
):
    return await TagService.get_popular_tags(limit)
