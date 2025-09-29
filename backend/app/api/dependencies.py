from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import AsyncClient
from supabase_auth import User

from app.db.database import get_service_client, get_client_for_token

security = HTTPBearer()


def get_supabase_service_client() -> AsyncClient:
    """Get the Supabase service client."""
    return get_service_client()


async def get_supabase_request_client(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AsyncClient:
    """Get Supabase client bound to the current request's user token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )

    token = credentials.credentials
    try:
        return await get_client_for_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    service_client: AsyncClient = Depends(get_supabase_service_client),
) -> User:
    """Get the current user from the request."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )

    token = credentials.credentials
    try:
        user = await service_client.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    if not user or not user.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
        )

    return user.user


async def get_current_user_id(user: User = Depends(get_current_user)) -> UUID:
    return UUID(user.id)
