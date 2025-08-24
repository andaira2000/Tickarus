# app/db/database.py
from supabase import create_client, Client
from typing import Optional
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
    """
    Initialize a base Supabase client with project URL and anon/service key.
    This client is never mutated with a user token.
    """
    global _base_client
    if _base_client is None:
        _base_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase base client initialized")
    return _base_client


def get_supabase() -> Client:
    """
    Return the request-scoped client if present; otherwise the base client.
    """
    client = _request_client.get()
    return client or init_supabase()


def client_for_token(access_token: str) -> Client:
    """
    Create a fresh client bound to the caller's JWT (so RLS sees auth.uid()).
    """
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.postgrest.auth(access_token)
    return client


def bind_request_client(access_token: str) -> None:
    """
    Store a request-scoped client in the context var. Call this early per request.
    """
    _request_client.set(client_for_token(access_token))


# ---------- NEW: safe execute helpers for supabase-py v2 ----------


def exec_query(q):
    """
    Execute a PostgREST query and return the APIResponse.
    Errors are raised as HTTP 400 (unless the SDK throws a specific type).
    """
    try:
        return q.execute()
    except Exception as e:
        # supabase-py v2 raises exceptions for non-2xx responses
        msg = str(e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def exec_single(q, not_found_msg: str = "Not found"):
    """
    Execute a .single() query. If no rows, map to HTTP 404.
    """
    try:
        return q.single().execute()
    except Exception as e:
        msg = str(e)
        # PostgREST "no rows" commonly shows as "Results contain 0 rows"
        if "0 rows" in msg or "no rows" in msg.lower():
            raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_msg)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)
