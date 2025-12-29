from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.models.fee_payment import FeePayment
from app.models.institution import Institution
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse, CourseEnrollmentCreate, FeePaymentCreate
from app.dependencies import get_current_user, check_resource_access, can_manage_students
from app.services.storage_service import storage

router = APIRouter()


def generate_student_id(db: Session, institution_id: UUID) -> str:
    """
    Generate unique student ID in format: RTS-DISTRICT-INST-MM-YYYY-NNNN
    Example: RTS-NAL-RCC-12-2025-0001

    Components:
    - RTS: Prefix
    - NAL: District code (from institution)
    - RCC: Institution initials (first letter of each word)
    - 12: Month
    - 2025: Year
    - 0001: Sequential number
    """
    # Get institution
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Get district code (default to "UNK" if not set)
    district_code = institution.district_code.upper() if institution.district_code else "UNK"

    # Create institution code from first letter of each word
    # Example: "Rajtech Computer Center" -> "RCC"
    words = institution.name.split()
    inst_code = ''.join([word[0].upper() for word in words if word])

    # Get current month and year
    now = datetime.now()
    current_month = now.strftime("%m")  # 01-12
    current_year = now.year

    # Find the last student ID for this institution, month, and year
    last_student = db.query(Student).filter(
        Student.student_id.like(f"RTS-{district_code}-{inst_code}-{current_month}-{current_year}-%")
    ).order_by(Student.student_id.desc()).first()

    if last_student and last_student.student_id:
        # Extract the sequence number and increment
        try:
            last_seq = int(last_student.student_id.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            new_seq = 1
    else:
        new_seq = 1

    # Format: RTS-DISTRICT-INST-MM-YYYY-0001
    student_id = f"RTS-{district_code}-{inst_code}-{current_month}-{current_year}-{new_seq:04d}"

    return student_id


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new student
    Requires: Franchise Admin or Accountant role
    Auto-generates student ID in format: RTS-INST-MM-YYYY-NNNN
    """
    can_manage_students(current_user)
    check_resource_access(current_user, student_data.institution_id)

    # Generate unique student ID
    student_id = generate_student_id(db, student_data.institution_id)

    new_student = Student(
        user_id=student_data.user_id,
        institution_id=student_data.institution_id,
        student_id=student_id,  # Auto-generated
        date_of_birth=student_data.date_of_birth,
        guardian_name=student_data.guardian_name,
        guardian_phone=student_data.guardian_phone,
        address=student_data.address
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student


@router.get("/", response_model=List[StudentResponse])
def list_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List students filtered by institution"""
    if current_user.role == "super_admin":
        students = db.query(Student).all()
    else:
        students = db.query(Student).filter(
            Student.institution_id == current_user.institution_id
        ).all()

    return students


@router.get("/search", response_model=StudentResponse)
def search_student_by_id(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search student by student_id (custom ID like RTS-NAL-RCC-12-2025-0001)
    Used by receptionist to find student for payment recording
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found with this ID")

    # Check access - staff can only access students from their institution
    if current_user.role != "super_admin":
        check_resource_access(current_user, student.institution_id)

    return student


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student details"""
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: UUID,
    update_data: StudentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update student details
    Requires: Franchise Admin, Accountant, or Receptionist role
    Can manually edit student_id with uniqueness validation
    """
    can_manage_students(current_user)

    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    # If student_id is being updated, validate uniqueness
    update_dict = update_data.dict(exclude_unset=True)
    if 'student_id' in update_dict and update_dict['student_id'] != student.student_id:
        # Check if the new student_id already exists
        existing_student = db.query(Student).filter(
            Student.student_id == update_dict['student_id'],
            Student.id != student_id  # Exclude current student
        ).first()

        if existing_student:
            raise HTTPException(
                status_code=400,
                detail=f"Student ID '{update_dict['student_id']}' already exists. Please use a different ID."
            )

    for key, value in update_dict.items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return student


@router.post("/{student_id}/photo")
def upload_student_photo(
    student_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload student photo"""
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    # Upload file
    file_url = storage.upload_file(file.file, "photos", file.filename)
    student.photo_url = file_url

    db.commit()
    db.refresh(student)

    return {"photo_url": file_url}


@router.post("/{student_id}/enroll")
def enroll_in_course(
    student_id: UUID,
    enrollment: CourseEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enroll student in a course"""
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    # Check if already enrolled
    existing = db.query(StudentCourse).filter(
        StudentCourse.student_id == student_id,
        StudentCourse.course_id == enrollment.course_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    new_enrollment = StudentCourse(
        student_id=student_id,
        course_id=enrollment.course_id
    )

    db.add(new_enrollment)
    db.commit()

    return {"message": "Enrolled successfully"}


@router.post("/{student_id}/payments")
def record_payment(
    student_id: UUID,
    payment: FeePaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record fee payment"""
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    new_payment = FeePayment(
        student_id=student_id,
        course_id=payment.course_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        notes=payment.notes
    )

    db.add(new_payment)
    db.commit()

    return {"message": "Payment recorded successfully"}
