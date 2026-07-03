"""
Staff management. Only super_admin / institution_director manage staff
(docs/01 §3 permission matrix); staff_manager may read the roster (needed
for attendance marking).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import joinedload
from typing import List, Optional
from uuid import UUID

from app.dependencies import require_roles, STAFF_ADMIN_ROLES, MANAGER_ROLES
from app.models.staff import Staff
from app.models.user import User
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse
from app.services.auth_service import hash_password
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def staff_to_response(staff: Staff) -> dict:
    """Convert Staff model to response dict with user information"""
    return {
        "id": staff.id,
        "user_id": staff.user_id,
        "institution_id": staff.institution_id,
        "position": staff.position,
        "daily_rate": float(staff.daily_rate) if staff.daily_rate else 0.0,
        "join_date": staff.joining_date,
        "created_at": staff.created_at,
        "updated_at": staff.updated_at,
        "full_name": staff.user.full_name,
        "email": staff.user.email,
        "phone": staff.user.phone,
        "role": staff.user.role,
        "status": "active" if staff.user.is_active else "inactive",
    }


def _get_staff_or_404(ctx: TenantContext, staff_id: UUID) -> Staff:
    staff = ctx.q(Staff).options(joinedload(Staff.user)).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.post(
    "/",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def create_staff(
    staff_data: StaffCreate,
    institution_id: Optional[UUID] = None,  # honored ONLY for super_admin
    ctx: TenantContext = Depends(get_tenant),
):
    """
    Add a staff member (creates both User and Staff records).
    Role is restricted to staff / staff_manager / receptionist by the schema.
    """
    target_institution = ctx.require_institution_id(institution_id)

    existing_user = ctx.db.query(User).filter(User.email == staff_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {staff_data.email} already exists",
        )

    new_user = User(
        email=staff_data.email,
        hashed_password=hash_password(staff_data.phone),  # phone = default password
        full_name=staff_data.full_name,
        phone=staff_data.phone,
        role=staff_data.role,
        institution_id=target_institution,
        is_active=True,
    )
    ctx.db.add(new_user)
    ctx.db.flush()

    new_staff = Staff(
        user_id=new_user.id,
        institution_id=target_institution,
        position=staff_data.role,
        daily_rate=staff_data.daily_rate,
    )
    ctx.db.add(new_staff)

    ctx.db.commit()
    ctx.db.refresh(new_staff)
    ctx.db.refresh(new_staff, ["user"])

    return staff_to_response(new_staff)


@router.get(
    "/",
    response_model=List[StaffResponse],
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def list_staff(ctx: TenantContext = Depends(get_tenant)):
    """List staff in the caller's institution."""
    staff = ctx.q(Staff).options(joinedload(Staff.user)).all()
    return [staff_to_response(s) for s in staff]


@router.get(
    "/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def get_staff(
    staff_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return staff_to_response(_get_staff_or_404(ctx, staff_id))


@router.patch(
    "/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def update_staff(
    staff_id: UUID,
    update_data: StaffUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Update staff details including daily_rate (director+)."""
    staff = _get_staff_or_404(ctx, staff_id)

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(staff, key, value)

    ctx.db.commit()
    ctx.db.refresh(staff)
    return staff_to_response(staff)


@router.delete(
    "/{staff_id}",
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def delete_staff(
    staff_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Remove a staff member (director+)."""
    staff = _get_staff_or_404(ctx, staff_id)

    ctx.db.delete(staff)
    ctx.db.commit()
    return {"message": "Staff deleted successfully"}
