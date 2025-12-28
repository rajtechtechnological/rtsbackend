from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.models.fee_payment import FeePayment
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse, CourseEnrollmentCreate, FeePaymentCreate
from app.dependencies import get_current_user, check_resource_access, can_manage_students
from app.services.storage_service import storage

router = APIRouter()


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new student
    Requires: Franchise Admin or Accountant role
    """
    can_manage_students(current_user)
    check_resource_access(current_user, student_data.institution_id)

    new_student = Student(
        user_id=student_data.user_id,
        institution_id=student_data.institution_id,
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
    Requires: Franchise Admin or Accountant role
    """
    can_manage_students(current_user)

    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    for key, value in update_data.dict(exclude_unset=True).items():
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
