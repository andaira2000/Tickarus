from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.database import init_supabase
from app.api.dependencies import get_current_user

router = APIRouter()


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(user: UserRegister):
    """
    Email/password sign-up. Supabase may require email confirmation depending on your project settings.
    """
    supabase = init_supabase()
    try:
        resp = supabase.auth.sign_up(
            {
                "email": user.email,
                "password": user.password,
                "options": {
                    "data": {"full_name": user.full_name or user.email.split("@")[0]}
                },
            }
        )
        if not resp or not resp.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Sign-up failed"
            )
        return {"user_id": resp.user.id, "email": resp.user.email}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
def login(creds: UserLogin):
    """
    Email/password login. Returns access and refresh tokens.
    """
    supabase = init_supabase()
    try:
        session = supabase.auth.sign_in_with_password(
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
async def get_current_user_profile(current_user=Depends(get_current_user)):
    """
    Get current user's profile information from JWT token.
    """
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.user_metadata.get("full_name") if current_user.user_metadata else None,
            "email_confirmed_at": current_user.email_confirmed_at,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )
