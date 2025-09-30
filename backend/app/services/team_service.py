from typing import List
from uuid import UUID

from supabase import AsyncClient

from app.models.team import Team, TeamCreate, TeamUpdate, TeamMember, TeamRole


class TeamService:
    @staticmethod
    async def create_team(
        payload: TeamCreate, creator_user_id: UUID, supabase_client: AsyncClient
    ) -> Team:
        team = (
            await supabase_client.table("teams")
            .insert(
                {
                    "name": payload.name,
                    "description": payload.description,
                    "created_by": str(creator_user_id),
                },
                returning="representation",
            )
            .execute()
        ).data[0]

        return Team(**team)

    @staticmethod
    async def list_teams(supabase_client: AsyncClient) -> List[Team]:
        teams = (
            await supabase_client.table("teams")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        ).data
        return [Team(**team) for team in teams]

    @staticmethod
    async def update_team(
        team_id: UUID, patch: TeamUpdate, supabase_client: AsyncClient
    ) -> Team:
        payload = {}
        if patch.name is not None:
            payload["name"] = patch.name
        if patch.description is not None:
            payload["description"] = patch.description

        if not payload:
            team = (
                await supabase_client.table("teams")
                .select("*")
                .eq("id", str(team_id))
                .execute()
            ).data
            return Team(**team)

        team = (
            await supabase_client.table("teams")
            .update(payload, returning="representation")
            .eq("id", str(team_id))
            .execute()
        ).data[0]

        return Team(**team)

    @staticmethod
    async def list_members(
        team_id: UUID, supabase_client: AsyncClient
    ) -> List[TeamMember]:
        members = (
            await supabase_client.table("team_members")
            .select("*")
            .eq("team_id", str(team_id))
            .execute()
        ).data

        return [
            TeamMember(
                team_id=UUID(member["team_id"]),
                user_id=UUID(member["user_id"]),
                role=TeamRole(member["role"]),
                joined_at=member["joined_at"],
            )
            for member in members
        ]

    @staticmethod
    async def add_member(
        team_id: UUID, user_id: UUID, role: TeamRole, supabase_client: AsyncClient
    ) -> TeamMember:
        member = (
            await supabase_client.table("team_members")
            .insert(
                {"team_id": str(team_id), "user_id": str(user_id), "role": role.value},
                returning="representation",
            )
            .execute()
        ).data[0]

        return TeamMember(
            team_id=UUID(member["team_id"]),
            user_id=UUID(member["user_id"]),
            role=TeamRole(member["role"]),
            joined_at=member["joined_at"],
        )

    @staticmethod
    async def update_member(
        team_id: UUID, user_id: UUID, role: TeamRole, supabase_client: AsyncClient
    ) -> TeamMember:
        member = (
            await supabase_client.table("team_members")
            .update({"role": role.value}, returning="representation")
            .match({"team_id": str(team_id), "user_id": str(user_id)})
            .execute()
        ).data[0]

        return TeamMember(
            team_id=UUID(member["team_id"]),
            user_id=UUID(member["user_id"]),
            role=TeamRole(member["role"]),
            joined_at=member["joined_at"],
        )

    @staticmethod
    async def remove_member(
        team_id: UUID, user_id: UUID, supabase_client: AsyncClient
    ) -> None:
        await supabase_client.table("team_members").delete().match(
            {"team_id": str(team_id), "user_id": str(user_id)}
        ).execute()
