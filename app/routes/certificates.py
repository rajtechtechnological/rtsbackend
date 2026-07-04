"""
Certificates. Manager-only generation (F-01), tenant-scoped via the
denormalized institution_id, collision-free numbering via id_counters
(docs/02 §6). No stored PDFs — certificates are rendered on demand.
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.config import settings
from app.dependencies import require_roles, MANAGER_ROLES, ALL_ROLES
from app import ids
from app.models.certificate import Certificate
from app.models.course import Course
from app.models.institution import Institution
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.schemas.payroll import CertificateGenerate, CertificateResponse
from app.services.pdf_service import generate_certificate
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _own_student_row(ctx: TenantContext) -> Student:
    student = ctx.q(Student).filter(Student.user_id == ctx.user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found")
    return student


@router.post(
    "/generate",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def generate_certificate(
    cert_data: CertificateGenerate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Generate a certificate for a student (managers only, own institution)."""
    # Tenant isolation (F-01): student fetched via ctx.q — out-of-tenant = 404
    student = ctx.q(Student).filter(Student.id == cert_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    enrollment = ctx.db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.course_id == cert_data.course_id,
    ).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student not enrolled in this course")
    if enrollment.status != "completed":
        raise HTTPException(status_code=400, detail="Course not yet completed")

    existing_cert = ctx.db.query(Certificate).filter(
        Certificate.student_id == student.id,
        Certificate.course_id == cert_data.course_id,
    ).first()
    if existing_cert:
        raise HTTPException(status_code=400, detail="Certificate already generated")

    institution = ctx.db.query(Institution).filter(
        Institution.id == student.institution_id
    ).first()

    # Atomic, institution-scoped, never reused (F-05):
    # RTS-{DIST}-{INST}-CERT-{YYYY}-{NNNN}
    cert_number = ids.certificate_number(ctx.db, institution, date.today().year)

    new_certificate = Certificate(
        institution_id=student.institution_id,
        student_id=student.id,
        course_id=cert_data.course_id,
        certificate_number=cert_number,
        verification_code=secrets.token_urlsafe(16),
    )

    ctx.db.add(new_certificate)
    ctx.db.commit()
    ctx.db.refresh(new_certificate)
    return new_certificate


@router.get(
    "/",
    response_model=List[CertificateResponse],
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def list_certificates(
    student_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List certificates. Tenant-scoped; students only ever see their own."""
    query = ctx.q(Certificate)

    if ctx.user.role == "student":
        own = _own_student_row(ctx)
        query = query.filter(Certificate.student_id == own.id)

    if student_id:
        query = query.filter(Certificate.student_id == student_id)
    if course_id:
        query = query.filter(Certificate.course_id == course_id)

    return query.order_by(Certificate.created_at.desc()).all()


@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_certificate(
    certificate_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    certificate = ctx.q(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if ctx.user.role == "student":
        own = _own_student_row(ctx)
        if certificate.student_id != own.id:
            # Own-records-only: someone else's certificate is a 404
            raise HTTPException(status_code=404, detail="Certificate not found")

    return certificate


@router.get(
    "/{certificate_id}/certificate.pdf",
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def download_certificate(
    certificate_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Render and stream the certificate PDF on demand — no stored PDFs
    (docs/01 §2/§8): always regenerated from DB truth. Tenant-scoped;
    students may only fetch their OWN certificate. The verification_code is
    embedded as a QR pointing at the public verify page."""
    certificate = (
        ctx.q(Certificate)
        .options(
            joinedload(Certificate.student).joinedload(Student.user),
            joinedload(Certificate.course),
        )
        .filter(Certificate.id == certificate_id)
        .first()
    )
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if ctx.user.role == "student":
        own = _own_student_row(ctx)
        if certificate.student_id != own.id:
            # Own-records-only: someone else's certificate is a 404
            raise HTTPException(status_code=404, detail="Certificate not found")

    institution = ctx.db.query(Institution).filter(
        Institution.id == certificate.institution_id
    ).first()

    student = certificate.student
    course = certificate.course

    cert_info = {
        "institution_name": institution.name if institution else "",
        "student_name": student.user.full_name if student and student.user else "N/A",
        "course_name": course.name if course else "N/A",
        "certificate_number": certificate.certificate_number,
        "issue_date": certificate.issue_date,
        "verification_code": certificate.verification_code,
        # Public QR-verify page served by the frontend
        "verify_url": f"{settings.FRONTEND_URL.rstrip('/')}/verify/{certificate.verification_code}",
    }

    pdf_buffer = generate_certificate(cert_info)
    filename = f"Certificate_{certificate.certificate_number}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
