import logging

from supabase import acreate_client, AsyncClient

from app.config import settings

logger = logging.getLogger(__name__)

service_client: AsyncClient | None = None


async def init_supabase_service_client():
    global service_client
    if not service_client:
        service_client = await acreate_client(
            settings.supabase_url, settings.supabase_service_key
        )
        logger.info("Initialized Supabase service client")


def get_service_client() -> AsyncClient:
    if not service_client:
        raise Exception("supabase service client not initialized")
    return service_client


async def get_client_for_token(access_token: str) -> AsyncClient:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)
    client.postgrest.auth(access_token)
    return client
