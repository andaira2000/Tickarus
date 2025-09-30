from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from supabase import AsyncClient
from supabase_auth import User

from app.api.dependencies import get_current_user, get_supabase_service_client

router = APIRouter()


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(
    user: UserRegister,
    supabase_service_client: AsyncClient = Depends(get_supabase_service_client),
):
    """Email/password registration. Returns user ID and email."""
    try:
        result = await supabase_service_client.auth.sign_up(
            {
                "email": user.email,
                "password": user.password,
                "options": {
                    "data": {"full_name": user.full_name or user.email.split("@")[0]}
                },
            }
        )
        if not result.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Sign-up failed"
            )

        # Profile and actor creation are handled by Supabase trigger functions.

        return {"user_id": result.user.id, "email": result.user.email}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(
    creds: UserLogin,
    supabase_service_client: AsyncClient = Depends(get_supabase_service_client),
):
    """Email/password login. Returns access and refresh tokens."""
    try:
        session = await supabase_service_client.auth.sign_in_with_password(
            {"email": creds.email, "password": creds.password}
        )
        if not session or not session.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        return {
            "access_token": session.session.access_token,
            "refresh_token": session.session.refresh_token,
            "token_type": "bearer",
            "expires_in": session.session.expires_in,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile informatio"""
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": (
                current_user.user_metadata.get("full_name")
                if current_user.user_metadata
                else None
            ),
            "email_confirmed_at": current_user.email_confirmed_at,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}",
        )
