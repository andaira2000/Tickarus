from typing import Optional, Dict, Any, List
from uuid import UUID
from fastapi import HTTPException, status as http_status
from app.db.database import (
    get_supabase,
    get_service_client,
    exec_query,
    exec_single,
    first_row,
)
from app.models.actor import Actor, ActorCreate, ActorUpdate, ActorType, ActorInfo
from app.models.system_user import SystemUser


class ActorService:
    @staticmethod
    def _c():
        return get_supabase()

    @classmethod
    async def get_actor(cls, actor_id: UUID) -> Actor:
        """Get an actor by ID with expanded profile/system_user data"""
        c = cls._c()

        # Get the basic actor record
        resp = exec_single(
            c.table("actors").select("*").eq("id", str(actor_id)),
            not_found_msg="Actor not found",
        )
        actor_data = resp.data

        # Expand with profile or system_user data
        if actor_data["actor_type"] == "human" and actor_data["profile_id"]:
            profile_resp = (
                c.table("profiles")
                .select("*")
                .eq("id", actor_data["profile_id"])
                .execute()
            )
            if profile_resp.data:
                actor_data["profile"] = profile_resp.data[0]
        elif actor_data["actor_type"] == "system" and actor_data["system_user_id"]:
            system_user_resp = (
                c.table("system_users")
                .select("*")
                .eq("id", actor_data["system_user_id"])
                .execute()
            )
            if system_user_resp.data:
                actor_data["system_user"] = system_user_resp.data[0]

        return Actor(**actor_data)

    @classmethod
    async def get_actor_info(cls, actor_id: UUID) -> ActorInfo:
        """Get simplified actor info for display purposes"""
        actor = await cls.get_actor(actor_id)

        if actor.actor_type == ActorType.HUMAN and actor.profile:
            return ActorInfo.from_human_profile(actor.id, actor.profile)
        elif actor.actor_type == ActorType.SYSTEM and actor.system_user:
            return ActorInfo.from_system_user(actor.id, actor.system_user)
        else:
            # Fallback for missing data - shouldn't happen with proper data
            raise HTTPException(
                http_status.HTTP_404_NOT_FOUND,
                f"Actor {actor_id} is missing required profile or system_user data"
            )

    @classmethod
    async def get_actor_for_user(cls, user_id: UUID) -> Optional[Actor]:
        """Get the actor record for a human user (by profile_id)"""
        c = cls._c()

        result = (
            c.table("actors")
            .select("*")
            .eq("profile_id", str(user_id))
            .eq("actor_type", "human")
            .execute()
        )
        if result.data:
            return Actor(**result.data[0])
        return None

    @classmethod
    async def get_actor_for_system_user(cls, system_user_id: UUID, client=None) -> Optional[Actor]:
        """Get the actor record for a system user"""
        c = client or cls._c()

        result = (
            c.table("actors")
            .select("*")
            .eq("system_user_id", str(system_user_id))
            .eq("actor_type", "system")
            .execute()
        )
        if result.data:
            return Actor(**result.data[0])
        return None

    @classmethod
    async def create_actor(cls, data: ActorCreate, client=None) -> Actor:
        """Create a new actor record"""
        c = client or cls._c()

        payload = {
            "actor_type": data.actor_type.value,
            "profile_id": str(data.profile_id) if data.profile_id else None,
            "system_user_id": str(data.system_user_id) if data.system_user_id else None,
        }

        resp = exec_query(c.table("actors").insert(payload, returning="representation"))
        row = first_row(resp.data)
        if not row:
            raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Create actor failed")
        return Actor(**row)

    @classmethod
    async def get_multiple_actor_info(
        cls, actor_ids: List[UUID]
    ) -> Dict[UUID, ActorInfo]:
        """Get actor info for multiple actors efficiently"""
        if not actor_ids:
            return {}

        c = cls._c()

        # Get all actors with their related data in one query
        actors_resp = (
            c.table("actors")
            .select(
                """
            *,
            profiles:profile_id(id, full_name, username, avatar_url),
            system_users:system_user_id(id, name, type, description)
        """
            )
            .in_("id", [str(aid) for aid in actor_ids])
            .execute()
        )

        result = {}
        for actor_data in actors_resp.data:
            actor_id = UUID(actor_data["id"])

            if actor_data["actor_type"] == "human" and actor_data.get("profiles"):
                result[actor_id] = ActorInfo.from_human_profile(
                    actor_id, actor_data["profiles"]
                )
            elif actor_data["actor_type"] == "system" and actor_data.get(
                "system_users"
            ):
                result[actor_id] = ActorInfo.from_system_user(
                    actor_id, actor_data["system_users"]
                )
            else:
                # Fallback
                result[actor_id] = ActorInfo(
                    id=actor_id,
                    actor_type=ActorType(actor_data["actor_type"]),
                    display_name="Unknown",
                    is_system=actor_data["actor_type"] == "system",
                )

        return result

    @classmethod
    def get_current_user_actor_id(cls) -> Optional[UUID]:
        """Helper to get the current authenticated user's actor ID"""
        # This would be used in API endpoints to get the current user's actor
        # For now, this is a placeholder - would need to be implemented based on auth system
        pass
