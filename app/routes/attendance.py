"""
Staff attendance. Marking requires staff_manager+ (permission matrix); every
staff role may view their OWN records ("View own attendance/payslips").
Attendance rows carry a denormalized institution_id so ctx.q and RLS apply
directly.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import date
from uuid import UUID

from app.dependencies import require_roles, MANAGER_ROLES, ALL_STAFF_ROLES
from app.models.attendance import StaffAttendance
from app.models.staff import Staff
from app.schemas.staff import AttendanceCreate, AttendanceBatchCreate, AttendanceResponse
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _own_staff_row(ctx: TenantContext) -> Optional[Staff]:
    return ctx.q(Staff).filter(Staff.user_id == ctx.user.id).first()


def _scoped_staff_or_404(ctx: TenantContext, staff_id: UUID) -> Staff:
    staff = ctx.q(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.post(
    "/",
    response_model=AttendanceResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def mark_attendance(
    attendance_data: AttendanceCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Mark attendance for a single staff member (staff_manager+)."""
    staff = _scoped_staff_or_404(ctx, attendance_data.staff_id)

    existing = ctx.db.query(StaffAttendance).filter(
        StaffAttendance.staff_id == staff.id,
        StaffAttendance.date == attendance_data.date,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked for this date")

    new_attendance = StaffAttendance(
        institution_id=staff.institution_id,
        staff_id=staff.id,
        date=attendance_data.date,
        status=attendance_data.status,
        marked_by=ctx.user.id,
        notes=attendance_data.notes,
    )

    ctx.db.add(new_attendance)
    ctx.db.commit()
    ctx.db.refresh(new_attendance)
    return new_attendance


@router.post(
    "/batch",
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def mark_attendance_batch(
    batch_data: AttendanceBatchCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Mark attendance for multiple staff members at once (staff_manager+)."""
    marked_count = 0

    for item in batch_data.attendance:
        staff_id = UUID(str(item.get("staff_id")))
        att_status = item.get("status")
        if att_status not in ("present", "absent", "half_day", "leave"):
            continue

        # Tenant-scoped: silently skip staff outside the caller's institution
        staff = ctx.q(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            continue

        existing = ctx.db.query(StaffAttendance).filter(
            StaffAttendance.staff_id == staff.id,
            StaffAttendance.date == batch_data.date,
        ).first()
        if not existing:
            ctx.db.add(StaffAttendance(
                institution_id=staff.institution_id,
                staff_id=staff.id,
                date=batch_data.date,
                status=att_status,
                marked_by=ctx.user.id,
            ))
            marked_count += 1

    ctx.db.commit()
    return {"message": f"Marked attendance for {marked_count} staff members"}


@router.get(
    "/",
    response_model=List[AttendanceResponse],
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def list_attendance(
    staff_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List attendance. Managers see the institution; staff/receptionist see
    only their own records."""
    query = ctx.q(StaffAttendance)

    if ctx.user.role not in MANAGER_ROLES:
        own = _own_staff_row(ctx)
        if not own:
            return []
        query = query.filter(StaffAttendance.staff_id == own.id)
    elif staff_id:
        query = query.filter(StaffAttendance.staff_id == staff_id)

    if start_date:
        query = query.filter(StaffAttendance.date >= start_date)
    if end_date:
        query = query.filter(StaffAttendance.date <= end_date)

    return query.order_by(StaffAttendance.date.desc()).all()


@router.get(
    "/summary",
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_attendance_summary(
    staff_id: UUID,
    month: int,
    year: int,
    ctx: TenantContext = Depends(get_tenant),
):
    """Monthly attendance summary (used for payroll calculation)."""
    staff = _scoped_staff_or_404(ctx, staff_id)

    # Non-managers may only see their own summary
    if ctx.user.role not in MANAGER_ROLES and staff.user_id != ctx.user.id:
        raise HTTPException(status_code=404, detail="Staff not found")

    return _attendance_summary(ctx, staff.id, month, year)


def _attendance_summary(ctx: TenantContext, staff_id: UUID, month: int, year: int) -> dict:
    from sqlalchemy import func, extract

    summary = (
        ctx.db.query(
            StaffAttendance.status,
            func.count(StaffAttendance.id).label("count"),
        )
        .filter(
            StaffAttendance.staff_id == staff_id,
            extract("month", StaffAttendance.date) == month,
            extract("year", StaffAttendance.date) == year,
        )
        .group_by(StaffAttendance.status)
        .all()
    )

    result = {
        "days_present": 0,
        "days_absent": 0,
        "days_half": 0,
        "days_leave": 0,
    }

    for att_status, count in summary:
        if att_status == "present":
            result["days_present"] = count
        elif att_status == "absent":
            result["days_absent"] = count
        elif att_status == "half_day":
            result["days_half"] = count
        elif att_status == "leave":
            result["days_leave"] = count

    return result
