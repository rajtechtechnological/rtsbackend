"""
Fee payments. Payments carry a denormalized institution_id (docs/02) so they
are queried directly via ctx.q; receipt numbers come from the atomic
id_counters helper (docs/02 §6).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app import ids
from app.dependencies import require_roles, PAYMENT_ROLES, ALL_STAFF_ROLES
from app.models.course import Course
from app.models.fee_payment import FeePayment
from app.models.institution import Institution
from app.models.student import Student
from app.schemas.student import FeePaymentCreate, FeePaymentResponse
from app.services.pdf_service import generate_payment_receipt
from app.tenancy import TenantContext, get_tenant

router = APIRouter()

VALID_METHODS = ["online", "offline", "cash", "upi", "card", "bank_transfer"]


def _get_payment_or_404(ctx: TenantContext, payment_id: UUID) -> FeePayment:
    payment = ctx.q(FeePayment).filter(FeePayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post(
    "/",
    response_model=FeePaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(PAYMENT_ROLES))],
)
def record_payment(
    payment_data: FeePaymentCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Record a student fee payment (receptionist+). The payment's
    institution_id comes from the tenant-scoped student row — never from
    the request."""
    student = ctx.q(Student).filter(Student.id == payment_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    course = ctx.db.query(Course).filter(
        Course.id == payment_data.course_id,
        (Course.institution_id == student.institution_id) | (Course.institution_id.is_(None)),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if payment_data.payment_method not in VALID_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method. Must be one of: {', '.join(VALID_METHODS)}",
        )

    if payment_data.payment_method in ["online", "upi", "card"] and not payment_data.transaction_id:
        raise HTTPException(
            status_code=400,
            detail=f"Transaction ID is required for {payment_data.payment_method} payments",
        )

    institution = ctx.db.query(Institution).filter(
        Institution.id == student.institution_id
    ).first()
    receipt_number = ids.receipt_number(ctx.db, institution, datetime.now().year)

    new_payment = FeePayment(
        institution_id=student.institution_id,
        student_id=student.id,
        course_id=payment_data.course_id,
        amount=payment_data.amount,
        paid_at=payment_data.paid_at or datetime.now().date(),
        payment_method=payment_data.payment_method,
        transaction_id=payment_data.transaction_id,
        receipt_number=receipt_number,
        notes=payment_data.notes,
        recorded_by=ctx.user.id,
    )

    ctx.db.add(new_payment)
    ctx.db.commit()
    ctx.db.refresh(new_payment)
    return new_payment


@router.get(
    "/",
    response_model=List[FeePaymentResponse],
    dependencies=[Depends(require_roles(PAYMENT_ROLES))],
)
def list_payments(
    student_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    payment_method: Optional[str] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """List fee payments in the caller's institution."""
    query = ctx.q(FeePayment)

    if student_id:
        query = query.filter(FeePayment.student_id == student_id)
    if course_id:
        query = query.filter(FeePayment.course_id == course_id)
    if payment_method:
        query = query.filter(FeePayment.payment_method == payment_method)

    return query.order_by(FeePayment.created_at.desc()).all()


@router.get(
    "/student/{student_id}/summary",
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_student_payment_summary(
    student_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Total paid / total fee / balance per enrolled course."""
    student = ctx.q(Student).options(joinedload(Student.user)).filter(
        Student.id == student_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    payment_summary = (
        ctx.db.query(
            FeePayment.course_id,
            Course.name.label("course_name"),
            Course.fee_amount.label("total_fee"),
            func.sum(FeePayment.amount).label("total_paid"),
            func.count(FeePayment.id).label("payment_count"),
        )
        .join(Course, FeePayment.course_id == Course.id)
        .filter(FeePayment.student_id == student.id)
        .group_by(FeePayment.course_id, Course.name, Course.fee_amount)
        .all()
    )

    result = []
    for record in payment_summary:
        total_fee = float(record.total_fee) if record.total_fee else 0
        total_paid = float(record.total_paid) if record.total_paid else 0
        balance = total_fee - total_paid
        result.append({
            "course_id": record.course_id,
            "course_name": record.course_name,
            "total_fee": total_fee,
            "total_paid": total_paid,
            "balance": balance,
            "payment_count": record.payment_count,
            "status": "paid" if balance <= 0 else "pending",
        })

    return {
        "student_id": student_id,
        "student_name": student.user.full_name if student.user else None,
        "courses": result,
    }


@router.get(
    "/{payment_id}",
    response_model=FeePaymentResponse,
    dependencies=[Depends(require_roles(PAYMENT_ROLES))],
)
def get_payment(
    payment_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _get_payment_or_404(ctx, payment_id)


@router.get(
    "/{payment_id}/receipt.pdf",
    dependencies=[Depends(require_roles(PAYMENT_ROLES + ["student"]))],
)
@router.get(
    "/{payment_id}/receipt",
    include_in_schema=False,  # legacy alias for /receipt.pdf
    dependencies=[Depends(require_roles(PAYMENT_ROLES + ["student"]))],
)
def download_receipt(
    payment_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Generate and stream the PDF receipt on demand — in-memory only, never
    written to disk, no stored URL (docs/01 §2). Receptionist+ may print any
    receipt in their institution; a student may fetch their OWN receipts."""
    payment = (
        ctx.q(FeePayment)
        .options(
            joinedload(FeePayment.student).joinedload(Student.user),
            joinedload(FeePayment.course),
            joinedload(FeePayment.recorded_by_user),
        )
        .filter(FeePayment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    student = payment.student

    # Own-records-only for students: someone else's receipt is a 404
    if ctx.user.role == "student":
        if not student or student.user_id != ctx.user.id:
            raise HTTPException(status_code=404, detail="Payment not found")
    institution = ctx.db.query(Institution).filter(
        Institution.id == payment.institution_id
    ).first()

    course = payment.course
    total_fee = float(course.fee_amount) if course and course.fee_amount else 0

    total_paid_query = ctx.db.query(func.sum(FeePayment.amount)).filter(
        FeePayment.student_id == payment.student_id,
        FeePayment.course_id == payment.course_id,
    ).scalar()
    total_paid = float(total_paid_query) if total_paid_query else 0
    balance = total_fee - total_paid

    payment_info = {
        "receipt_number": payment.receipt_number,
        "payment_date": payment.paid_at,
        "student_name": student.user.full_name if student and student.user else "N/A",
        "course_name": course.name if course else "N/A",
        "total_fee": total_fee,
        "amount_paid": float(payment.amount),
        "balance": balance,
        "payment_method": payment.payment_method,
        "transaction_id": payment.transaction_id,
        "institution_name": institution.name if institution else "RAJTECH COMPUTER CENTER",
        "institution_address": institution.address if institution else "",
        "institution_phone": institution.contact_phone if institution else "",
        "created_by_name": payment.recorded_by_user.full_name if payment.recorded_by_user else "Staff",
    }

    pdf_buffer = generate_payment_receipt(payment_info)
    filename = f"Receipt_{payment.receipt_number}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
