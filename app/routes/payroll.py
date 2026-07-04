"""
Payroll. Generation/approval requires director+ (permission matrix); every
staff role may view their OWN payslips. Payroll rows carry a denormalized
institution_id so ctx.q and RLS apply directly.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.dependencies import require_roles, STAFF_ADMIN_ROLES, ALL_STAFF_ROLES, MANAGER_ROLES
from app.models.institution import Institution
from app.models.payroll import PayrollRecord
from app.models.staff import Staff
from app.routes.attendance import _attendance_summary
from app.schemas.payroll import PayrollGenerate, PayrollResponse
from app.services.pdf_service import generate_payslip
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


@router.post(
    "/generate",
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def generate_payroll(
    payroll_data: PayrollGenerate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Generate payroll for a month/year (director+). institution_id in the
    body is honored only for super_admin."""
    institution_id = ctx.require_institution_id(payroll_data.institution_id)
    staff_list = ctx.db.query(Staff).filter(Staff.institution_id == institution_id).all()

    generated_count = 0
    for staff in staff_list:
        existing = ctx.db.query(PayrollRecord).filter(
            PayrollRecord.staff_id == staff.id,
            PayrollRecord.month == payroll_data.month,
            PayrollRecord.year == payroll_data.year,
        ).first()
        if existing:
            continue

        summary = _attendance_summary(ctx, staff.id, payroll_data.month, payroll_data.year)
        days_present = summary["days_present"]
        days_half = summary["days_half"]
        daily_rate = staff.daily_rate or Decimal(0)
        total_amount = (Decimal(days_present) * daily_rate) + (
            Decimal(days_half) * daily_rate * Decimal("0.5")
        )

        ctx.db.add(PayrollRecord(
            institution_id=staff.institution_id,
            staff_id=staff.id,
            month=payroll_data.month,
            year=payroll_data.year,
            days_present=days_present,
            days_half=days_half,
            total_amount=total_amount,
        ))
        generated_count += 1

    ctx.db.commit()
    return {"message": f"Generated payroll for {generated_count} staff members"}


@router.get(
    "/",
    response_model=List[PayrollResponse],
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def list_payroll(
    month: Optional[int] = None,
    year: Optional[int] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List payroll records. Managers see the institution; staff/receptionist
    see only their own payslips."""
    query = ctx.q(PayrollRecord)

    if ctx.user.role not in MANAGER_ROLES:
        own = ctx.q(Staff).filter(Staff.user_id == ctx.user.id).first()
        if not own:
            return []
        query = query.filter(PayrollRecord.staff_id == own.id)

    if month:
        query = query.filter(PayrollRecord.month == month)
    if year:
        query = query.filter(PayrollRecord.year == year)

    return query.order_by(PayrollRecord.generated_at.desc()).all()


def _get_payroll_scoped(ctx: TenantContext, payroll_id: UUID) -> PayrollRecord:
    payroll = ctx.q(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll record not found")

    if ctx.user.role not in MANAGER_ROLES:
        own = ctx.q(Staff).filter(Staff.user_id == ctx.user.id).first()
        if not own or payroll.staff_id != own.id:
            # Own-records-only: someone else's payslip is a 404
            raise HTTPException(status_code=404, detail="Payroll record not found")

    return payroll


@router.get(
    "/{payroll_id}",
    response_model=PayrollResponse,
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_payroll(
    payroll_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _get_payroll_scoped(ctx, payroll_id)


@router.get(
    "/{payroll_id}/payslip.pdf",
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def download_payslip(
    payroll_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Generate and stream the PDF payslip on demand — in-memory only, never
    stored (docs/01 §2). Managers may fetch any payslip in their institution;
    staff/receptionist only their OWN (_get_payroll_scoped)."""
    payroll = _get_payroll_scoped(ctx, payroll_id)

    staff = (
        ctx.q(Staff)
        .options(joinedload(Staff.user))
        .filter(Staff.id == payroll.staff_id)
        .first()
    )
    institution = ctx.db.query(Institution).filter(
        Institution.id == payroll.institution_id
    ).first()

    payslip_info = {
        "institution_name": institution.name if institution else "",
        "institution_address": institution.address if institution else "",
        "institution_phone": institution.contact_phone if institution else "",
        "staff_name": staff.user.full_name if staff and staff.user else "Staff",
        "position": staff.position if staff else None,
        "month": payroll.month,
        "year": payroll.year,
        "days_present": payroll.days_present,
        "days_half": payroll.days_half,
        "daily_rate": staff.daily_rate if staff else 0,
        "total_amount": payroll.total_amount,
        "generated_at": payroll.generated_at,
    }

    pdf_buffer = generate_payslip(payslip_info)
    filename = f"Payslip_{payroll.year}_{payroll.month:02d}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
