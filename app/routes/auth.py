"""
Authentication (docs/01 §5, F-11/F-12).

- Access token: JWT, 15 min, payload {sub, role, institution_id}.
- Refresh token: opaque 256-bit random value stored hashed (sha256) in
  refresh_tokens; delivered as an httpOnly Secure SameSite=Lax cookie with
  a 30-day expiry; ROTATED on every /refresh; revoked on logout.
- Login is refused while the user's institution is suspended.
- No public self-signup: user accounts are created by super_admin
  (institutions/staff/students each have their own staff-driven creation
  flows).
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.institution import Institution
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate
from app.services.auth_service import (
    create_access_token_for_user,
    get_valid_refresh_token,
    hash_password,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)

router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"
# Cookie is only ever needed by the auth endpoints themselves.
REFRESH_COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    # Secure + SameSite=Lax is correct both for direct https access and for
    # the recommended prod setup where Next.js proxies /api/* to this app
    # (same-origin, first-party cookie — see docs/07-DEPLOYMENT.md).
    # REFRESH_COOKIE_SECURE=false is ONLY for local http dev.
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "institution_id": str(user.institution_id) if user.institution_id else None,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a user (super_admin only — there is no public self-signup,
    docs/01 §5). Role is validated against the canonical 6-role enum by the
    schema AND the DB CHECK constraint.
    """
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Mirror the DB CHECK with a friendly error:
    # institution_id is NULL iff role='super_admin'
    if (user_data.role == "super_admin") != (user_data.institution_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="super_admin must have no institution_id; every other role requires one",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        institution_id=user_data.institution_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """
    Login: returns a 15-min access token (payload {sub, role, institution_id})
    and sets the httpOnly refresh cookie.
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Suspended franchise => login refused for all of its users (docs/02 §2)
    if user.institution_id is not None:
        institution = db.query(Institution).filter(
            Institution.id == user.institution_id
        ).first()
        if institution is not None and institution.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This institution is suspended. Contact RTS head office.",
            )

    access_token = create_access_token_for_user(user)
    raw_refresh = issue_refresh_token(db, user)
    db.commit()

    _set_refresh_cookie(response, raw_refresh)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_payload(user),
    }


@router.post("/refresh")
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
):
    """
    Exchange a valid refresh cookie for a new access token. The refresh
    token is ROTATED: the presented one is revoked and a new one is set.
    """
    record = get_valid_refresh_token(db, refresh_token or "")
    if record is None:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if user.institution_id is not None:
        institution = db.query(Institution).filter(
            Institution.id == user.institution_id
        ).first()
        if institution is not None and institution.status == "suspended":
            _clear_refresh_cookie(response)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This institution is suspended. Contact RTS head office.",
            )

    new_raw = rotate_refresh_token(db, record, user)
    access_token = create_access_token_for_user(user)
    db.commit()

    _set_refresh_cookie(response, new_raw)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _user_payload(user),
    }


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
):
    """Logout: revoke the presented refresh token and clear the cookie."""
    if refresh_token:
        revoke_refresh_token(db, refresh_token)
        db.commit()
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile"""
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile"""
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    if update_data.phone is not None:
        current_user.phone = update_data.phone

    if update_data.email is not None:
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = update_data.email

    db.commit()
    db.refresh(current_user)
    return current_user
