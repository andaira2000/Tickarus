from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from app.api.dependencies import get_current_user_id
from app.models.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamRole
from app.services.team_service import TeamService

router = APIRouter()


@router.post("/", response_model=Team)
async def create_team(
    payload: TeamCreate, current_user_id: UUID = Depends(get_current_user_id)
):
    return await TeamService.create_team(payload, current_user_id)


@router.get("/", response_model=List[Team])
async def list_teams(current_user_id: UUID = Depends(get_current_user_id)):
    return await TeamService.list_teams()


@router.patch("/{team_id}", response_model=Team)
async def update_team(
    team_id: UUID,
    patch: TeamUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
):
    return await TeamService.update_team(team_id, patch)


@router.get("/{team_id}/members", response_model=List[TeamMember])
async def list_members(
    team_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    return await TeamService.list_members(team_id)


@router.post("/{team_id}/members/{user_id}", response_model=TeamMember)
async def add_member(
    team_id: UUID,
    user_id: UUID,
    role: TeamRole = TeamRole.MEMBER,
    current_user_id: UUID = Depends(get_current_user_id),
):
    return await TeamService.add_member(team_id, user_id, role)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMember)
async def update_member(
    team_id: UUID,
    user_id: UUID,
    role: TeamRole,
    current_user_id: UUID = Depends(get_current_user_id),
):
    return await TeamService.update_member(team_id, user_id, role)


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: UUID, user_id: UUID, current_user_id: UUID = Depends(get_current_user_id)
):
    await TeamService.remove_member(team_id, user_id)
    return {"message": "Member removed"}
