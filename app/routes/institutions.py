"""
Institution management. Institutions are the tenant root (no institution_id
of their own): super_admin manages all; other roles can only read/update
their own institution. The director is the users row with
role='institution_director' (F-07) — enforced by the partial unique index.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from typing import List
from uuid import UUID

from app.dependencies import require_roles, STAFF_ADMIN_ROLES, ALL_ROLES
from app.models.institution import Institution
from app.models.staff import Staff
from app.models.student import Student
from app.models.user import User
from app.schemas.institution import (
    InstitutionCreate, InstitutionUpdate, InstitutionStatusUpdate, InstitutionResponse,
)
from app.services.auth_service import hash_password
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _get_institution_scoped(ctx: TenantContext, institution_id: UUID) -> Institution:
    """Institution visible to the caller: super_admin any, others own only.
    Out-of-scope rows are a 404."""
    institution = ctx.db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    if ctx.institution_id is not None and institution.id != ctx.institution_id:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


def _director_of(ctx: TenantContext, institution_id: UUID):
    return ctx.db.query(User).filter(
        User.institution_id == institution_id,
        User.role == "institution_director",
    ).first()


@router.post(
    "/",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
def create_institution(
    institution_data: InstitutionCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """
    Create a new institution (super_admin only).
    Auto-creates the franchise director user:
    - Email: institution's contact_email
    - Password: institution's contact_phone (changed later)
    - Role: institution_director (exactly one per institution)
    """
    if not institution_data.contact_email:
        raise HTTPException(status_code=400, detail="contact_email is required to create the director user")
    if not institution_data.contact_phone:
        raise HTTPException(status_code=400, detail="contact_phone is required to set the director's initial password")

    existing_user = ctx.db.query(User).filter(User.email == institution_data.contact_email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {institution_data.contact_email} already exists",
        )

    duplicate = ctx.db.query(Institution).filter(
        Institution.district_code == institution_data.district_code.upper(),
        Institution.code == institution_data.code.upper(),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An institution with this district/code already exists")

    new_institution = Institution(
        name=institution_data.name,
        district_code=institution_data.district_code.upper(),
        code=institution_data.code.upper(),
        address=institution_data.address,
        contact_email=institution_data.contact_email,
        contact_phone=institution_data.contact_phone,
    )
    ctx.db.add(new_institution)
    ctx.db.flush()

    director = User(
        email=institution_data.contact_email,
        hashed_password=hash_password(institution_data.contact_phone),
        full_name=f"{institution_data.name} Director",
        phone=institution_data.contact_phone,
        role="institution_director",
        institution_id=new_institution.id,
        is_active=True,
    )
    ctx.db.add(director)

    ctx.db.commit()
    ctx.db.refresh(new_institution)
    return new_institution


@router.get(
    "/",
    response_model=List[InstitutionResponse],
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def list_institutions(ctx: TenantContext = Depends(get_tenant)):
    """List institutions (super_admin sees all, others see their own)."""
    query = ctx.db.query(Institution)
    if ctx.institution_id is not None:
        query = query.filter(Institution.id == ctx.institution_id)
    return query.all()


@router.get(
    "/stats/summary",
    dependencies=[Depends(require_roles(["super_admin"]))],
)
def get_institutions_summary(ctx: TenantContext = Depends(get_tenant)):
    """Cross-institution analytics (super_admin only)."""
    institutions = ctx.db.query(Institution).all()

    institutions_with_stats = []
    for inst in institutions:
        staff_count = ctx.db.query(func.count(Staff.id)).filter(
            Staff.institution_id == inst.id
        ).scalar() or 0
        student_count = ctx.db.query(func.count(Student.id)).filter(
            Student.institution_id == inst.id
        ).scalar() or 0
        director = _director_of(ctx, inst.id)

        institutions_with_stats.append({
            "id": str(inst.id),
            "name": inst.name,
            "district_code": inst.district_code,
            "code": inst.code,
            "address": inst.address,
            "contact_email": inst.contact_email,
            "contact_phone": inst.contact_phone,
            "director_name": director.full_name if director else None,
            "staff_count": staff_count,
            "student_count": student_count,
            "status": inst.status,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
        })

    return {
        "institutions": institutions_with_stats,
        "total_franchises": len(institutions_with_stats),
        "total_staff": sum(i["staff_count"] for i in institutions_with_stats),
        "total_students": sum(i["student_count"] for i in institutions_with_stats),
    }


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_institution(
    institution_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _get_institution_scoped(ctx, institution_id)


@router.patch(
    "/{institution_id}",
    response_model=InstitutionResponse,
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def update_institution(
    institution_id: UUID,
    update_data: InstitutionUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Update institution contact details (super_admin or own director)."""
    institution = _get_institution_scoped(ctx, institution_id)

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(institution, key, value)

    ctx.db.commit()
    ctx.db.refresh(institution)
    return institution


@router.patch(
    "/{institution_id}/status",
    response_model=InstitutionResponse,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
def set_institution_status(
    institution_id: UUID,
    payload: InstitutionStatusUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Suspend / reactivate a franchise (super_admin only). While suspended,
    login is refused for all of its users (docs/02 §2)."""
    institution = _get_institution_scoped(ctx, institution_id)
    institution.status = payload.status
    ctx.db.commit()
    ctx.db.refresh(institution)
    return institution


@router.delete(
    "/{institution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(["super_admin"]))],
)
def delete_institution(
    institution_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Delete institution (super_admin only). Users, students, staff, courses
    etc. are removed via FK ON DELETE CASCADE."""
    institution = ctx.db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    ctx.db.delete(institution)
    ctx.db.commit()
    return None
