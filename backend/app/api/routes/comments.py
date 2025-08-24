from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from app.api.dependencies import get_current_user_id
from app.models.comment import Comment, CommentCreate, CommentUpdate
from app.services.comment_service import CommentService

router = APIRouter()


@router.post("/", response_model=Comment)
async def create_comment(
    payload: CommentCreate, current_user_id: UUID = Depends(get_current_user_id)
):
    return await CommentService.create_comment(payload, current_user_id)


@router.get("/ticket/{ticket_id}", response_model=List[Comment])
async def list_comments(
    ticket_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    return await CommentService.list_comments(ticket_id)


@router.patch("/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: UUID,
    patch: CommentUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
):
    return await CommentService.update_comment(comment_id, patch, current_user_id)


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    await CommentService.delete_comment(comment_id, current_user_id)
    return {"message": "Comment deleted"}
