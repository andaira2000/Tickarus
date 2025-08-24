from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.database import init_supabase

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
