from uuid import UUID

from supabase import AsyncClient

from app.models.actor import Actor


class ActorService:
    @staticmethod
    async def get_actor_for_human_user(
        user_id: UUID, supabase_client: AsyncClient
    ) -> Actor:
        """Get the actor record for a human user from the profile_id."""
        result = (
            await supabase_client.table("actors")
            .select("*")
            .eq("profile_id", str(user_id))
            .eq("actor_type", "human")
            .single()
            .execute()
        )

        return Actor(**result.data)

    @staticmethod
    async def get_actor_for_system_user(
        system_user_id: UUID, supabase_client: AsyncClient
    ) -> Actor:
        """Get the actor record for a system user from the system_user_id."""
        result = await (
            supabase_client.table("actors")
            .select("*")
            .eq("system_user_id", str(system_user_id))
            .eq("actor_type", "system")
            .single()
            .execute()
        )

        return Actor(**result.data)
