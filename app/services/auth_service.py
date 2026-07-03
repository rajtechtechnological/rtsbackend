"""
Password hashing + JWT access tokens + opaque refresh tokens (docs/01 §5).

Access token: 15 min, payload {sub, role, institution_id} — role and
institution ride in the token so the frontend can route without an extra
call, but the backend always re-reads the user row.

Refresh token: 256-bit random opaque value; ONLY its sha256 hash is stored
in refresh_tokens. Rotated on every use, revoked on logout.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Access tokens (JWT)
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token_for_user(user: User) -> str:
    """Access token with the canonical payload {sub, role, institution_id}."""
    return create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "institution_id": str(user.institution_id) if user.institution_id else None,
    })


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify JWT access token"""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Refresh tokens (opaque, hashed at rest, rotated on use)
# ---------------------------------------------------------------------------

def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_refresh_token(db, user: User) -> str:
    """Create + persist a refresh token; returns the RAW value (cookie-bound,
    never stored)."""
    raw_token = secrets.token_urlsafe(32)  # 256 bits of randomness
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=_hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.flush()
    return raw_token


def get_valid_refresh_token(db, raw_token: str) -> Optional[RefreshToken]:
    """Look up a presented refresh token; None if unknown/revoked/expired."""
    if not raw_token:
        return None
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == _hash_refresh_token(raw_token)
    ).first()
    if record is None or record.revoked_at is not None:
        return None
    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        return None
    return record


def rotate_refresh_token(db, record: RefreshToken, user: User) -> str:
    """Rotation (docs/01 §5): revoke the presented token, issue a fresh one."""
    record.revoked_at = datetime.now(timezone.utc)
    return issue_refresh_token(db, user)


def revoke_refresh_token(db, raw_token: str) -> None:
    """Revoke a single token (logout)."""
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == _hash_refresh_token(raw_token)
    ).first()
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)


def revoke_all_refresh_tokens(db, user_id) -> None:
    """Revoke every active session for a user (password change etc.)."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: datetime.now(timezone.utc)})
