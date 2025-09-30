from fastapi import APIRouter, Depends
from typing import List
from uuid import UUID
from app.api.dependencies import get_current_user_id, get_supabase_request_client
from app.models.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamRole
from app.services.team_service import TeamService

router = APIRouter()


@router.post("", response_model=Team)
async def create_team(
    payload: TeamCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    supabase_client=Depends(get_supabase_request_client),
):
    return await TeamService.create_team(payload, current_user_id, supabase_client)


@router.get("", response_model=List[Team])
async def list_teams(supabase_client=Depends(get_supabase_request_client)):
    return await TeamService.list_teams(supabase_client)


@router.patch("/{team_id}", response_model=Team)
async def update_team(
    team_id: UUID,
    patch: TeamUpdate,
    supabase_client=Depends(get_supabase_request_client),
):
    return await TeamService.update_team(team_id, patch, supabase_client)


@router.get("/{team_id}/members", response_model=List[TeamMember])
async def list_members(
    team_id: UUID, supabase_client=Depends(get_supabase_request_client)
):
    return await TeamService.list_members(team_id, supabase_client)


@router.post("/{team_id}/members/{user_id}", response_model=TeamMember)
async def add_member(
    team_id: UUID,
    user_id: UUID,
    role: TeamRole = TeamRole.MEMBER,
    supabase_client=Depends(get_supabase_request_client),
):
    return await TeamService.add_member(team_id, user_id, role, supabase_client)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMember)
async def update_member(
    team_id: UUID,
    user_id: UUID,
    role: TeamRole,
    supabase_client=Depends(get_supabase_request_client),
):
    return await TeamService.update_member(team_id, user_id, role, supabase_client)


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: UUID, user_id: UUID, supabase_client=Depends(get_supabase_request_client)
):
    await TeamService.remove_member(team_id, user_id, supabase_client)
    return {"message": "Member removed"}
