from supabase import create_client, Client
from typing import Optional, Any
import logging
import contextvars

from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)

# Global base client (no user token attached)
_base_client: Optional[Client] = None

# Request-scoped client carrying the caller's JWT for RLS
_request_client: contextvars.ContextVar[Optional[Client]] = contextvars.ContextVar(
    "_request_client", default=None
)


def init_supabase() -> Client:
    global _base_client
    if _base_client is None:
        _base_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase base client initialized")
    return _base_client


def get_supabase() -> Client:
    client = _request_client.get()
    return client or init_supabase()


def client_for_token(access_token: str) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.postgrest.auth(access_token)
    return client


def bind_request_client(access_token: str) -> None:
    _request_client.set(client_for_token(access_token))


def get_service_client() -> Client:
    """Get Supabase client with service role key for system operations"""
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ---------- Safe execute helpers for supabase-py v2 ----------


def exec_query(q):
    """Execute a PostgREST query and return the APIResponse."""
    try:
        return q.execute()
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


def exec_single(q, not_found_msg: str = "Not found"):
    """
    Execute a SELECT with .single(). If no rows, raise 404.
    Usage: exec_single(client.table("t").select("*").eq("id", "..."))
    """
    try:
        return q.single().execute()
    except Exception as e:
        msg = str(e)
        if "0 rows" in msg or "no rows" in msg.lower():
            raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_msg)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def first_row(data: Any):
    """Return the first row from APIResponse.data for mutation queries."""
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None
