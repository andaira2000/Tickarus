from typing import List
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import get_supabase, exec_query, exec_single, first_row
from app.models.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamRole


class TeamService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def create_team(cls, payload: TeamCreate, creator_user_id: UUID) -> Team:
        c = cls._c()
        resp = exec_query(
            c.table("teams").insert(
                {
                    "name": payload.name,
                    "description": payload.description,
                    "created_by": str(creator_user_id),
                },
                returning="representation",
            )
        )
        row = first_row(resp.data)
        if not row:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Create team failed")
        return Team(**row)

    @classmethod
    async def list_teams(cls) -> List[Team]:
        c = cls._c()
        resp = exec_query(c.table("teams").select("*").order("created_at", desc=True))
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
            resp = exec_single(
                c.table("teams").select("*").eq("id", str(team_id)),
                not_found_msg="Team not found",
            )
            return Team(**resp.data)

        resp = exec_query(
            c.table("teams")
            .update(payload, returning="representation")
            .eq("id", str(team_id))
        )
        row = first_row(resp.data)
        if not row:
            # id not found or no row returned -> fetch to confirm
            exec_single(
                c.table("teams").select("*").eq("id", str(team_id)),
                not_found_msg="Team not found",
            )
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Update team failed")
        return Team(**row)

    @classmethod
    async def list_members(cls, team_id: UUID) -> List[TeamMember]:
        c = cls._c()
        resp = exec_query(
            c.table("team_members").select("*").eq("team_id", str(team_id))
        )
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
        resp = exec_query(
            c.table("team_members").insert(
                {"team_id": str(team_id), "user_id": str(user_id), "role": role.value},
                returning="representation",
            )
        )
        d = first_row(resp.data)
        if not d:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Add member failed")
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
        resp = exec_query(
            c.table("team_members")
            .update({"role": role.value}, returning="representation")
            .match({"team_id": str(team_id), "user_id": str(user_id)})
        )
        d = first_row(resp.data)
        if not d:
            exec_single(
                c.table("team_members")
                .select("*")
                .match({"team_id": str(team_id), "user_id": str(user_id)}),
                not_found_msg="Membership not found",
            )
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST, "Update member failed"
            )
        return TeamMember(
            team_id=UUID(d["team_id"]),
            user_id=UUID(d["user_id"]),
            role=TeamRole(d["role"]),
            joined_at=d["joined_at"],
        )

    @classmethod
    async def remove_member(cls, team_id: UUID, user_id: UUID) -> None:
        c = cls._c()
        exec_query(
            c.table("team_members")
            .delete()
            .match({"team_id": str(team_id), "user_id": str(user_id)})
        )
