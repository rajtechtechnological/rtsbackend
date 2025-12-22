from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse
from app.dependencies import get_current_user, check_resource_access

router = APIRouter()


@router.post("/", response_model=StaffResponse)
def create_staff(
    staff_data: StaffCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new staff member"""
    check_resource_access(current_user, staff_data.institution_id)

    new_staff = Staff(
        user_id=staff_data.user_id,
        institution_id=staff_data.institution_id,
        position=staff_data.position,
        daily_rate=staff_data.daily_rate
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return new_staff


@router.get("/", response_model=List[StaffResponse])
def list_staff(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List staff filtered by institution"""
    if current_user.role == "super_admin":
        staff = db.query(Staff).all()
    else:
        staff = db.query(Staff).filter(
            Staff.institution_id == current_user.institution_id
        ).all()

    return staff


@router.get("/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get staff details"""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    return staff


@router.patch("/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: UUID,
    update_data: StaffUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update staff details including daily_rate"""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(staff, key, value)

    db.commit()
    db.refresh(staff)

    return staff


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove staff member"""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    db.delete(staff)
    db.commit()

    return {"message": "Staff deleted successfully"}
