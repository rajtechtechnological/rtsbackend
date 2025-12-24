from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.institution import Institution
from app.models.student import Student
from app.models.staff import Staff
from app.schemas.institution import InstitutionCreate, InstitutionUpdate, InstitutionResponse
from app.dependencies import get_current_user, require_roles, check_institution_access

router = APIRouter()


@router.post("/", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def create_institution(
    institution_data: InstitutionCreate,
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """
    Create a new institution (super_admin only)
    """
    new_institution = Institution(
        name=institution_data.name,
        address=institution_data.address,
        contact_email=institution_data.contact_email,
        contact_phone=institution_data.contact_phone,
        director_id=institution_data.director_id
    )

    db.add(new_institution)
    db.commit()
    db.refresh(new_institution)

    return new_institution


@router.get("/", response_model=List[InstitutionResponse])
def list_institutions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List institutions (super_admin sees all, others see their own)
    """
    if current_user.role == "super_admin":
        institutions = db.query(Institution).all()
    else:
        institutions = db.query(Institution).filter(
            Institution.id == current_user.institution_id
        ).all()

    return institutions


@router.get("/stats/summary")
def get_institutions_summary(
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """
    Get summary stats for all institutions (super_admin only)
    """
    # Get all institutions with their stats
    institutions = db.query(Institution).all()
    
    institutions_with_stats = []
    for inst in institutions:
        # Count staff for this institution
        staff_count = db.query(func.count(Staff.id)).filter(
            Staff.institution_id == inst.id
        ).scalar() or 0
        
        # Count students for this institution
        student_count = db.query(func.count(Student.id)).filter(
            Student.institution_id == inst.id
        ).scalar() or 0
        
        # Get director info
        director_name = None
        if inst.director_id:
            director = db.query(User).filter(User.id == inst.director_id).first()
            if director:
                director_name = director.full_name
        
        institutions_with_stats.append({
            "id": str(inst.id),
            "name": inst.name,
            "address": inst.address,
            "contact_email": inst.contact_email,
            "contact_phone": inst.contact_phone,
            "director_name": director_name,
            "staff_count": staff_count,
            "student_count": student_count,
            "status": "active",  # You can add a status field to the model if needed
            "created_at": inst.created_at.isoformat() if inst.created_at else None
        })
    
    # Calculate totals
    total_staff = sum(i["staff_count"] for i in institutions_with_stats)
    total_students = sum(i["student_count"] for i in institutions_with_stats)
    
    return {
        "institutions": institutions_with_stats,
        "total_franchises": len(institutions_with_stats),
        "total_staff": total_staff,
        "total_students": total_students
    }


@router.get("/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get institution details
    """
    institution = db.query(Institution).filter(Institution.id == institution_id).first()

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found"
        )

    # Check access
    check_institution_access(current_user, institution.id)

    return institution


@router.patch("/{institution_id}", response_model=InstitutionResponse)
def update_institution(
    institution_id: str,
    update_data: InstitutionUpdate,
    current_user: User = Depends(require_roles(["super_admin", "institution_director"])),
    db: Session = Depends(get_db)
):
    """
    Update institution details
    """
    institution = db.query(Institution).filter(Institution.id == institution_id).first()

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found"
        )

    # Check access
    check_institution_access(current_user, institution.id)

    # Update fields
    if update_data.name is not None:
        institution.name = update_data.name
    if update_data.address is not None:
        institution.address = update_data.address
    if update_data.contact_email is not None:
        institution.contact_email = update_data.contact_email
    if update_data.contact_phone is not None:
        institution.contact_phone = update_data.contact_phone
    if update_data.director_id is not None:
        institution.director_id = update_data.director_id

    db.commit()
    db.refresh(institution)

    return institution


@router.delete("/{institution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_institution(
    institution_id: str,
    current_user: User = Depends(require_roles(["super_admin"])),
    db: Session = Depends(get_db)
):
    """
    Delete institution (super_admin only)
    """
    institution = db.query(Institution).filter(Institution.id == institution_id).first()

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found"
        )

    db.delete(institution)
    db.commit()

    return None
