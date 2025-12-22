from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.staff import Staff
from app.models.payroll import PayrollRecord
from app.schemas.payroll import PayrollGenerate, PayrollResponse
from app.dependencies import get_current_user
from app.routes.attendance import get_attendance_summary
from decimal import Decimal

router = APIRouter()


@router.post("/generate")
def generate_payroll(
    payroll_data: PayrollGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate payroll for a specific month/year"""
    # Get all staff in the institution (or all if super_admin)
    if payroll_data.institution_id:
        staff_list = db.query(Staff).filter(
            Staff.institution_id == payroll_data.institution_id
        ).all()
    elif current_user.role == "super_admin":
        staff_list = db.query(Staff).all()
    else:
        staff_list = db.query(Staff).filter(
            Staff.institution_id == current_user.institution_id
        ).all()

    generated_count = 0

    for staff in staff_list:
        # Check if payroll already exists
        existing = db.query(PayrollRecord).filter(
            PayrollRecord.staff_id == staff.id,
            PayrollRecord.month == payroll_data.month,
            PayrollRecord.year == payroll_data.year
        ).first()

        if existing:
            continue  # Skip if already generated

        # Get attendance summary
        summary = get_attendance_summary(
            staff_id=staff.id,
            month=payroll_data.month,
            year=payroll_data.year,
            db=db
        )

        # Calculate total amount
        days_present = summary["days_present"]
        days_half = summary["days_half"]
        daily_rate = staff.daily_rate or Decimal(0)

        total_amount = (Decimal(days_present) * daily_rate) + (Decimal(days_half) * daily_rate * Decimal(0.5))

        # Create payroll record
        payroll = PayrollRecord(
            staff_id=staff.id,
            month=payroll_data.month,
            year=payroll_data.year,
            days_present=days_present,
            days_half=days_half,
            total_amount=total_amount
        )

        db.add(payroll)
        generated_count += 1

    db.commit()

    return {"message": f"Generated payroll for {generated_count} staff members"}


@router.get("/", response_model=List[PayrollResponse])
def list_payroll(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List payroll records with optional filters"""
    query = db.query(PayrollRecord)

    # Filter by institution
    if current_user.role != "super_admin":
        query = query.join(Staff).filter(Staff.institution_id == current_user.institution_id)

    if month:
        query = query.filter(PayrollRecord.month == month)

    if year:
        query = query.filter(PayrollRecord.year == year)

    payroll_records = query.order_by(PayrollRecord.generated_at.desc()).all()

    return payroll_records


@router.get("/{payroll_id}", response_model=PayrollResponse)
def get_payroll(
    payroll_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payroll details"""
    payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()

    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll record not found")

    return payroll


@router.post("/{payroll_id}/generate-payslip")
def generate_payslip(
    payroll_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate PDF payslip for a payroll record"""
    payroll = db.query(PayrollRecord).filter(PayrollRecord.id == payroll_id).first()

    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll record not found")

    # TODO: Implement PDF generation using ReportLab
    # For now, return a placeholder
    return {"message": "PDF generation not yet implemented", "payroll_id": str(payroll_id)}
