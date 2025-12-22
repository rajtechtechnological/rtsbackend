from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.staff import Staff
from app.models.attendance import StaffAttendance
from app.schemas.staff import AttendanceCreate, AttendanceBatchCreate, AttendanceResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=AttendanceResponse)
def mark_attendance(
    attendance_data: AttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark attendance for a single staff member"""
    # Get staff to verify institution
    staff = db.query(Staff).filter(Staff.id == attendance_data.staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Check if already marked for this date
    existing = db.query(StaffAttendance).filter(
        StaffAttendance.staff_id == attendance_data.staff_id,
        StaffAttendance.date == attendance_data.date
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked for this date")

    new_attendance = StaffAttendance(
        staff_id=attendance_data.staff_id,
        date=attendance_data.date,
        status=attendance_data.status,
        marked_by=current_user.id,
        notes=attendance_data.notes
    )

    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    return new_attendance


@router.post("/batch")
def mark_attendance_batch(
    batch_data: AttendanceBatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark attendance for multiple staff members at once"""
    marked_count = 0

    for item in batch_data.attendance:
        staff_id = UUID(item.get("staff_id"))
        status = item.get("status")

        # Check if already marked
        existing = db.query(StaffAttendance).filter(
            StaffAttendance.staff_id == staff_id,
            StaffAttendance.date == batch_data.date
        ).first()

        if not existing:
            new_attendance = StaffAttendance(
                staff_id=staff_id,
                date=batch_data.date,
                status=status,
                marked_by=current_user.id
            )
            db.add(new_attendance)
            marked_count += 1

    db.commit()

    return {"message": f"Marked attendance for {marked_count} staff members"}


@router.get("/", response_model=List[AttendanceResponse])
def list_attendance(
    staff_id: UUID = None,
    start_date: date = None,
    end_date: date = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List attendance records with optional filters"""
    query = db.query(StaffAttendance)

    # Filter by institution
    if current_user.role != "super_admin":
        query = query.join(Staff).filter(Staff.institution_id == current_user.institution_id)

    # Apply filters
    if staff_id:
        query = query.filter(StaffAttendance.staff_id == staff_id)

    if start_date:
        query = query.filter(StaffAttendance.date >= start_date)

    if end_date:
        query = query.filter(StaffAttendance.date <= end_date)

    attendance_records = query.order_by(StaffAttendance.date.desc()).all()

    return attendance_records


@router.get("/summary")
def get_attendance_summary(
    staff_id: UUID,
    month: int,
    year: int,
    db: Session = Depends(get_db)
):
    """Get monthly attendance summary for payroll calculation"""
    from sqlalchemy import func, extract

    summary = db.query(
        StaffAttendance.status,
        func.count(StaffAttendance.id).label('count')
    ).filter(
        StaffAttendance.staff_id == staff_id,
        extract('month', StaffAttendance.date) == month,
        extract('year', StaffAttendance.date) == year
    ).group_by(StaffAttendance.status).all()

    result = {
        "days_present": 0,
        "days_absent": 0,
        "days_half": 0,
        "days_leave": 0
    }

    for status, count in summary:
        if status == "present":
            result["days_present"] = count
        elif status == "absent":
            result["days_absent"] = count
        elif status == "half_day":
            result["days_half"] = count
        elif status == "leave":
            result["days_leave"] = count

    return result
