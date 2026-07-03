"""
Authentication dependencies.

Per docs/01-SYSTEM-DESIGN.md §3 this module exposes ONLY get_current_user and
require_roles — the loose per-capability helpers (can_manage_students,
check_resource_access, ...) were deleted because using them was optional
(that is how F-01 happened). Every router declares its role gate in the
decorator, and tenant scoping happens exclusively through
app.tenancy.TenantContext.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from uuid import UUID
from typing import List

security = HTTPBearer()

# Canonical role groups (docs/01 §3 permission matrix)
MANAGER_ROLES = ["super_admin", "institution_director", "staff_manager"]
STAFF_ADMIN_ROLES = ["super_admin", "institution_director"]
STUDENT_MANAGER_ROLES = ["super_admin", "institution_director", "staff_manager", "receptionist"]
PAYMENT_ROLES = STUDENT_MANAGER_ROLES  # record fee payments, print receipts
EXAM_AUTHOR_ROLES = MANAGER_ROLES + ["staff"]  # staff may author; publishing needs manager+
ALL_STAFF_ROLES = ["super_admin", "institution_director", "staff_manager", "receptionist", "staff"]
ALL_ROLES = ALL_STAFF_ROLES + ["student"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Always re-read the user row so deactivation is immediate (docs/01 §5)
    user = db.query(User).filter(User.id == UUID(user_id)).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


def require_roles(allowed_roles: List[str]):
    """
    Dependency factory to check if user has required role
    Usage: Depends(require_roles(["super_admin", "institution_director"]))
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
