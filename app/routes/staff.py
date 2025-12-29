from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse
from app.dependencies import get_current_user, check_resource_access, can_manage_staff
from app.services.auth_service import hash_password

router = APIRouter()


def staff_to_response(staff: Staff) -> dict:
    """Convert Staff model to response dict with user information"""
    return {
        "id": staff.id,
        "user_id": staff.user_id,
        "institution_id": staff.institution_id,
        "position": staff.position,
        "daily_rate": float(staff.daily_rate) if staff.daily_rate else 0.0,
        "join_date": staff.joining_date,  # Use consistent join_date naming
        "created_at": staff.created_at,
        "updated_at": staff.updated_at,
        # User information
        "full_name": staff.user.full_name,
        "email": staff.user.email,
        "phone": staff.user.phone,
        "role": staff.user.role,
        "status": "active" if staff.user.is_active else "inactive",
    }


@router.post("/", response_model=StaffResponse)
def create_staff(
    staff_data: StaffCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new staff member (creates both User and Staff records)
    Requires: Franchise Admin role only

    Creates a User account with:
    - Email: provided email
    - Password: phone number (can be changed later)
    - Role: staff, staff_manager, or receptionist
    """
    can_manage_staff(current_user)
    check_resource_access(current_user, staff_data.institution_id)

    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == staff_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {staff_data.email} already exists"
        )

    # Validate role
    if staff_data.role not in ["staff", "staff_manager", "receptionist"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be either 'staff', 'staff_manager', or 'receptionist'"
        )

    # Create User record
    new_user = User(
        email=staff_data.email,
        hashed_password=hash_password(staff_data.phone),  # Use phone number as default password
        full_name=staff_data.full_name,
        phone=staff_data.phone,
        role=staff_data.role,
        institution_id=staff_data.institution_id,
        is_active=True
    )
    db.add(new_user)
    db.flush()  # Get the user ID without committing

    # Create Staff record
    new_staff = Staff(
        user_id=new_user.id,
        institution_id=staff_data.institution_id,
        position=staff_data.role,  # Use role as position
        daily_rate=staff_data.daily_rate
    )
    db.add(new_staff)

    # Commit both records atomically
    db.commit()
    db.refresh(new_staff)

    # Load the user relationship for response
    db.refresh(new_staff, ['user'])

    return staff_to_response(new_staff)


@router.get("/", response_model=List[StaffResponse])
def list_staff(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List staff filtered by institution"""
    if current_user.role == "super_admin":
        staff = db.query(Staff).options(joinedload(Staff.user)).all()
    else:
        staff = db.query(Staff).options(joinedload(Staff.user)).filter(
            Staff.institution_id == current_user.institution_id
        ).all()

    return [staff_to_response(s) for s in staff]


@router.get("/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get staff details"""
    staff = db.query(Staff).options(joinedload(Staff.user)).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    return staff_to_response(staff)


@router.patch("/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: UUID,
    update_data: StaffUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update staff details including daily_rate
    Requires: Franchise Admin role only
    """
    can_manage_staff(current_user)

    staff = db.query(Staff).options(joinedload(Staff.user)).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(staff, key, value)

    db.commit()
    db.refresh(staff)

    return staff_to_response(staff)


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove staff member
    Requires: Franchise Admin role only
    """
    can_manage_staff(current_user)

    staff = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    check_resource_access(current_user, staff.institution_id)

    db.delete(staff)
    db.commit()

    return {"message": "Staff deleted successfully"}
