from typing import List
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase
from app.models.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamRole


class TeamService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_team(cls, payload: TeamCreate, creator_id: UUID) -> Team:
        c = cls._c()
        resp = (
            c.table("teams")
            .insert(
                {
                    "name": payload.name,
                    "description": payload.description,
                    "created_by": str(
                        creator_id
                    ),  # will be enforced/filled by trigger too
                }
            )
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Create failed",
            )
        return Team(**resp.data)

    @classmethod
    async def list_teams(cls) -> List[Team]:
        c = cls._c()
        resp = c.table("teams").select("*").order("created_at", desc=True).execute()
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
        return [Team(**r) for r in (resp.data or [])]

    @classmethod
    async def update_team(cls, team_id: UUID, patch: TeamUpdate) -> Team:
        c = cls._c()
        payload = {}
        if patch.name is not None:
            payload["name"] = patch.name
        if patch.description is not None:
            payload["description"] = patch.description
        if not payload:
            resp = (
                c.table("teams").select("*").eq("id", str(team_id)).single().execute()
            )
            if resp.error or not resp.data:
                raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Team not found")
            return Team(**resp.data)

        resp = (
            c.table("teams")
            .update(payload)
            .eq("id", str(team_id))
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Update failed",
            )
        return Team(**resp.data)

    @classmethod
    async def list_members(cls, team_id: UUID) -> List[TeamMember]:
        c = cls._c()
        resp = c.table("team_members").select("*").eq("team_id", str(team_id)).execute()
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
        data = resp.data or []
        return [
            TeamMember(
                team_id=UUID(d["team_id"]),
                user_id=UUID(d["user_id"]),
                role=TeamRole(d["role"]),
                joined_at=d["joined_at"],
            )
            for d in data
        ]

    @classmethod
    async def add_member(
        cls, team_id: UUID, user_id: UUID, role: TeamRole
    ) -> TeamMember:
        c = cls._c()
        resp = (
            c.table("team_members")
            .insert(
                {"team_id": str(team_id), "user_id": str(user_id), "role": role.value}
            )
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Add member failed",
            )
        d = resp.data
        return TeamMember(
            team_id=UUID(d["team_id"]),
            user_id=UUID(d["user_id"]),
            role=TeamRole(d["role"]),
            joined_at=d["joined_at"],
        )

    @classmethod
    async def update_member(
        cls, team_id: UUID, user_id: UUID, role: TeamRole
    ) -> TeamMember:
        c = cls._c()
        resp = (
            c.table("team_members")
            .update({"role": role.value})
            .match({"team_id": str(team_id), "user_id": str(user_id)})
            .select("*")
            .single()
            .execute()
        )
        if resp.error or not resp.data:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                resp.error.message if resp.error else "Update member failed",
            )
        d = resp.data
        return TeamMember(
            team_id=UUID(d["team_id"]),
            user_id=UUID(d["user_id"]),
            role=TeamRole(d["role"]),
            joined_at=d["joined_at"],
        )

    @classmethod
    async def remove_member(cls, team_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        resp = (
            c.table("team_members")
            .delete()
            .match({"team_id": str(team_id), "user_id": str(user_id)})
            .execute()
        )
        if resp.error:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, resp.error.message)
