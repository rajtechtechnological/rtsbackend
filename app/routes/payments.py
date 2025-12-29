from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.fee_payment import FeePayment
from app.models.student import Student
from app.models.course import Course
from app.models.institution import Institution
from app.models.student_course import StudentCourse
from app.schemas.student import FeePaymentCreate, FeePaymentResponse
from app.dependencies import get_current_user, check_resource_access, can_record_payments
from app.services.pdf_service import generate_payment_receipt

router = APIRouter()


def generate_receipt_number(db: Session, institution_id: UUID) -> str:
    """
    Generate unique receipt number in format: RCT-INST-YYYY-NNNN
    """
    # Get institution
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Create institution code from name (first 3 letters uppercase)
    inst_code = institution.name[:3].upper().replace(" ", "")

    # Get current year
    current_year = datetime.now().year

    # Find the last receipt number for this institution and year
    last_payment = db.query(FeePayment).filter(
        FeePayment.receipt_number.like(f"RCT-{inst_code}-{current_year}-%")
    ).order_by(FeePayment.receipt_number.desc()).first()

    if last_payment and last_payment.receipt_number:
        # Extract the sequence number and increment
        try:
            last_seq = int(last_payment.receipt_number.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    # Format: RCT-INST-YYYY-0001
    receipt_number = f"RCT-{inst_code}-{current_year}-{new_seq:04d}"

    return receipt_number


@router.post("/", response_model=FeePaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    payment_data: FeePaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a new student fee payment
    Requires: Receptionist, Accountant, or Director role

    Automatically generates receipt number and validates payment details
    """
    can_record_payments(current_user)

    # Fetch student to get institution_id
    student = db.query(Student).filter(Student.id == payment_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check access to this student's institution
    check_resource_access(current_user, student.institution_id)

    # Fetch course to validate
    course = db.query(Course).filter(Course.id == payment_data.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Validate payment method
    valid_methods = ['online', 'offline', 'cash', 'upi', 'card', 'bank_transfer']
    if payment_data.payment_method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method. Must be one of: {', '.join(valid_methods)}"
        )

    # Validate transaction ID for online payments
    if payment_data.payment_method in ['online', 'upi', 'card'] and not payment_data.transaction_id:
        raise HTTPException(
            status_code=400,
            detail=f"Transaction ID is required for {payment_data.payment_method} payments"
        )

    # Generate receipt number
    receipt_number = generate_receipt_number(db, student.institution_id)

    # Create payment record
    new_payment = FeePayment(
        student_id=payment_data.student_id,
        course_id=payment_data.course_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date or datetime.now().date(),
        payment_method=payment_data.payment_method,
        transaction_id=payment_data.transaction_id,
        receipt_number=receipt_number,
        notes=payment_data.notes,
        created_by=current_user.id
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    # TODO: Generate PDF receipt and upload to cloud storage
    # For now, we'll add this in the next step

    return new_payment


@router.get("/", response_model=List[FeePaymentResponse])
def list_payments(
    student_id: Optional[UUID] = None,
    course_id: Optional[UUID] = None,
    payment_method: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List fee payments with optional filters
    Filtered by institution for non-super-admin users
    """
    query = db.query(FeePayment)

    # Filter by institution for non-super-admin
    if current_user.role != "super_admin":
        # Join with student to filter by institution
        query = query.join(Student).filter(
            Student.institution_id == current_user.institution_id
        )

    # Apply filters
    if student_id:
        query = query.filter(FeePayment.student_id == student_id)

    if course_id:
        query = query.filter(FeePayment.course_id == course_id)

    if payment_method:
        query = query.filter(FeePayment.payment_method == payment_method)

    payments = query.order_by(FeePayment.created_at.desc()).all()

    return payments


@router.get("/{payment_id}", response_model=FeePaymentResponse)
def get_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get payment details by ID
    """
    payment = db.query(FeePayment).filter(FeePayment.id == payment_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Check access
    student = db.query(Student).filter(Student.id == payment.student_id).first()
    if student:
        check_resource_access(current_user, student.institution_id)

    return payment


@router.get("/student/{student_id}/summary")
def get_student_payment_summary(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get payment summary for a student
    Shows total paid, total fees, and balance for each enrolled course
    """
    # Fetch student
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check access
    check_resource_access(current_user, student.institution_id)

    # Get all payments for this student grouped by course
    from sqlalchemy import func

    payment_summary = db.query(
        FeePayment.course_id,
        Course.name.label('course_name'),
        Course.fee_amount.label('total_fee'),
        func.sum(FeePayment.amount).label('total_paid'),
        func.count(FeePayment.id).label('payment_count')
    ).join(
        Course, FeePayment.course_id == Course.id
    ).filter(
        FeePayment.student_id == student_id
    ).group_by(
        FeePayment.course_id, Course.name, Course.fee_amount
    ).all()

    # Format response
    result = []
    for record in payment_summary:
        total_fee = float(record.total_fee) if record.total_fee else 0
        total_paid = float(record.total_paid) if record.total_paid else 0
        balance = total_fee - total_paid

        result.append({
            'course_id': record.course_id,
            'course_name': record.course_name,
            'total_fee': total_fee,
            'total_paid': total_paid,
            'balance': balance,
            'payment_count': record.payment_count,
            'status': 'paid' if balance <= 0 else 'pending'
        })

    return {
        'student_id': student_id,
        'student_name': student.user.full_name if student.user else None,
        'courses': result
    }


@router.get("/{payment_id}/receipt")
def download_receipt(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and download PDF receipt for a payment
    Receipt is generated on-demand, not stored
    """
    # Fetch payment with related data
    payment = db.query(FeePayment).options(
        joinedload(FeePayment.student).joinedload(Student.user),
        joinedload(FeePayment.course),
        joinedload(FeePayment.created_by_user)
    ).filter(FeePayment.id == payment_id).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Check access
    student = payment.student
    if student:
        check_resource_access(current_user, student.institution_id)

    # Get institution details
    institution = db.query(Institution).filter(
        Institution.id == student.institution_id
    ).first()

    # Calculate total fee and balance
    course = payment.course
    total_fee = float(course.fee_amount) if course and course.fee_amount else 0

    # Calculate total paid for this course
    from sqlalchemy import func
    total_paid_query = db.query(
        func.sum(FeePayment.amount)
    ).filter(
        FeePayment.student_id == payment.student_id,
        FeePayment.course_id == payment.course_id
    ).scalar()

    total_paid = float(total_paid_query) if total_paid_query else 0
    balance = total_fee - total_paid

    # Prepare data for PDF generation
    payment_data = {
        'receipt_number': payment.receipt_number,
        'payment_date': payment.payment_date,
        'student_name': student.user.full_name if student and student.user else 'N/A',
        'course_name': course.name if course else 'N/A',
        'total_fee': total_fee,
        'amount_paid': float(payment.amount),
        'balance': balance,
        'payment_method': payment.payment_method,
        'transaction_id': payment.transaction_id,
        'institution_name': institution.name if institution else 'RAJTECH COMPUTER CENTER',
        'institution_address': institution.address if institution else '',
        'institution_phone': institution.contact_phone if institution else '',
        'created_by_name': payment.created_by_user.full_name if payment.created_by_user else 'Staff',
    }

    # Generate PDF
    pdf_buffer = generate_payment_receipt(payment_data)

    # Return PDF as streaming response
    filename = f"Receipt_{payment.receipt_number}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
