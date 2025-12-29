from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token
from uuid import UUID
from typing import List

security = HTTPBearer()


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

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Fetch user from database
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


def check_institution_access(user: User, institution_id: UUID) -> bool:
    """
    Check if user has access to a specific institution
    """
    # Super admin can access all institutions
    if user.role == "super_admin":
        return True

    # Other users can only access their own institution
    if user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this institution"
        )

    return True


def check_resource_access(user: User, resource_institution_id: UUID) -> bool:
    """
    Check if user can access a resource belonging to an institution
    """
    return check_institution_access(user, resource_institution_id)


def can_manage_staff(user: User) -> bool:
    """
    Check if user can manage staff (add, edit, delete, set wages)
    Only franchise admin (institution_director) can manage staff
    """
    if user.role not in ["super_admin", "institution_director"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only franchise admins can manage staff"
        )
    return True


def can_manage_students(user: User) -> bool:
    """
    Check if user can manage students (add, edit, delete)
    Franchise admin, accountant (staff_manager), and receptionist can manage students
    Regular staff and students cannot
    """
    if user.role not in ["super_admin", "institution_director", "staff_manager", "receptionist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only franchise admins, accountants, and receptionists can manage students"
        )
    return True


def can_view_own_records_only(user: User, staff_id: UUID) -> bool:
    """
    Check if regular staff is trying to view only their own records
    Used for attendance and payroll access
    """
    # Super admin and franchise admin can view all
    if user.role in ["super_admin", "institution_director"]:
        return True

    # Staff and accountant can only view their own records
    # Find the staff record for this user
    if str(user.id) != str(staff_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own records"
        )

    return True


def can_record_payments(user: User) -> bool:
    """
    Check if user can record student payments
    Receptionist, Accountant (staff_manager), and Directors can record payments
    """
    if user.role not in ["super_admin", "institution_director", "staff_manager", "receptionist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only receptionists, accountants, and directors can record payments"
        )
    return True
