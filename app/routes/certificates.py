from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import date
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.models.student_course import StudentCourse
from app.schemas.payroll import CertificateGenerate, CertificateResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/generate")
def generate_certificate(
    cert_data: CertificateGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate certificate for a student"""
    # Verify student exists
    student = db.query(Student).filter(Student.id == cert_data.student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if student completed the course
    enrollment = db.query(StudentCourse).filter(
        StudentCourse.student_id == cert_data.student_id,
        StudentCourse.course_id == cert_data.course_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=400, detail="Student not enrolled in this course")

    if enrollment.status != "completed":
        raise HTTPException(status_code=400, detail="Course not yet completed")

    # Check if certificate already exists
    existing_cert = db.query(Certificate).filter(
        Certificate.student_id == cert_data.student_id,
        Certificate.course_id == cert_data.course_id
    ).first()

    if existing_cert:
        raise HTTPException(status_code=400, detail="Certificate already generated")

    # Generate unique certificate number
    year = date.today().year
    count = db.query(Certificate).filter(
        Certificate.course_id == cert_data.course_id
    ).count() + 1

    cert_number = f"CERT-{year}-{count:04d}"

    # TODO: Generate PDF certificate using ReportLab
    # For now, use placeholder URL
    cert_url = f"/certificates/{cert_number}.pdf"

    new_certificate = Certificate(
        student_id=cert_data.student_id,
        course_id=cert_data.course_id,
        certificate_url=cert_url,
        certificate_number=cert_number
    )

    db.add(new_certificate)
    db.commit()
    db.refresh(new_certificate)

    return {
        "message": "Certificate generated successfully",
        "certificate_number": cert_number,
        "certificate_url": cert_url
    }


@router.get("/", response_model=List[CertificateResponse])
def list_certificates(
    student_id: UUID = None,
    course_id: UUID = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List certificates with optional filters"""
    query = db.query(Certificate)

    # Filter by institution
    if current_user.role != "super_admin":
        query = query.join(Student).filter(Student.institution_id == current_user.institution_id)

    if student_id:
        query = query.filter(Certificate.student_id == student_id)

    if course_id:
        query = query.filter(Certificate.course_id == course_id)

    certificates = query.order_by(Certificate.created_at.desc()).all()

    return certificates


@router.get("/{certificate_id}", response_model=CertificateResponse)
def get_certificate(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get certificate details"""
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()

    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    return certificate
