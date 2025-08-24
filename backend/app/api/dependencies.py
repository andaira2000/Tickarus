from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from app.db.database import init_supabase, bind_request_client

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Validate JWT with Supabase and bind a request-scoped client carrying the caller's token,
    so RLS policies apply automatically to all service calls in this request.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )

    token = credentials.credentials
    base = init_supabase()
    try:
        user = base.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    if not user or not user.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
        )

    bind_request_client(token)
    return user.user


async def get_current_user_id(user=Depends(get_current_user)) -> UUID:
    return UUID(user.id)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Optional auth; returns None if missing/invalid.
    """
    if not credentials:
        return None
    try:
        token = credentials.credentials
        base = init_supabase()
        user = base.auth.get_user(token)
        if user and user.user:
            bind_request_client(token)
            return user.user
        return None
    except Exception:
        return None
