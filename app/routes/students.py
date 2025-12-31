from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.models.fee_payment import FeePayment
from app.models.course import Course
from app.models.course_module import CourseModule, StudentModuleProgress
from sqlalchemy import and_
from app.models.institution import Institution
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse, CourseEnrollmentCreate, FeePaymentCreate, StudentRegister
from app.services.auth_service import hash_password
from app.schemas.course_module import StudentCourseProgressResponse
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
        father_name=student_data.father_name,
        guardian_name=student_data.guardian_name,
        guardian_phone=student_data.guardian_phone,
        address=student_data.address,
        aadhar_number=student_data.aadhar_number,
        apaar_id=student_data.apaar_id,
        last_qualification=student_data.last_qualification,
        batch_time=student_data.batch_time,
        batch_month=student_data.batch_month,
        batch_year=student_data.batch_year,
        batch_identifier=student_data.batch_identifier,
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student


@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def register_student(
    data: StudentRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a new student (creates user + student in one call)
    - Creates user account with phone as default password
    - Creates student record with all details
    - Optionally enrolls in a course
    """
    can_manage_students(current_user)

    # Use current user's institution
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="User not associated with an institution")

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user with phone as default password (or a default if no phone)
    default_password = data.phone if data.phone else "student123"
    hashed_password = hash_password(default_password)

    new_user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        hashed_password=hashed_password,
        role="student",
        institution_id=institution_id,
        is_active=True
    )
    db.add(new_user)
    db.flush()  # Get the user ID without committing

    # Generate unique student ID
    student_id = generate_student_id(db, institution_id)

    # Create student record
    new_student = Student(
        user_id=new_user.id,
        institution_id=institution_id,
        student_id=student_id,
        date_of_birth=data.date_of_birth,
        father_name=data.father_name,
        guardian_name=data.guardian_name,
        guardian_phone=data.guardian_phone,
        address=data.address,
        aadhar_number=data.aadhar_number,
        apaar_id=data.apaar_id,
        last_qualification=data.last_qualification,
        batch_time=data.batch_time,
        batch_month=data.batch_month,
        batch_year=data.batch_year,
        batch_identifier=data.batch_identifier,
    )
    db.add(new_student)
    db.flush()

    # Optionally enroll in course
    if data.course_id:
        course = db.query(Course).filter(Course.id == data.course_id).first()
        if course:
            enrollment = StudentCourse(
                student_id=new_student.id,
                course_id=data.course_id
            )
            db.add(enrollment)

    db.commit()
    db.refresh(new_student)

    # Load relationships for response
    db.refresh(new_student)
    new_student.user = new_user

    return new_student


@router.get("/", response_model=List[StudentResponse])
def list_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List students filtered by institution"""
    if current_user.role == "super_admin":
        students = db.query(Student).options(
            joinedload(Student.user),
            joinedload(Student.course_enrollments)
        ).all()
    else:
        students = db.query(Student).options(
            joinedload(Student.user),
            joinedload(Student.course_enrollments)
        ).filter(
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
    student = db.query(Student).options(joinedload(Student.user)).filter(Student.student_id == student_id).first()

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
    student = db.query(Student).options(joinedload(Student.user)).filter(Student.id == student_id).first()

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


@router.get("/{student_id}/courses")
def get_student_courses(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all courses a student is enrolled in"""
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    check_resource_access(current_user, student.institution_id)

    # Get all course enrollments
    enrollments = db.query(StudentCourse).options(
        joinedload(StudentCourse.course)
    ).filter(StudentCourse.student_id == student_id).all()

    return enrollments


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


@router.get("/{student_id}/courses/{course_id}/progress", response_model=StudentCourseProgressResponse)
def get_student_course_progress(
    student_id: UUID,
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed progress for a student in a specific course"""
    # Verify student exists
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Multi-tenant check or student viewing own progress
    if current_user.role == "student":
        if student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only view your own progress")
    elif current_user.role != "super_admin":
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get all progress records for this student and course
    progress_records = db.query(StudentModuleProgress).join(
        CourseModule, StudentModuleProgress.module_id == CourseModule.id
    ).options(
        joinedload(StudentModuleProgress.module)
    ).filter(
        and_(
            StudentModuleProgress.student_id == student_id,
            StudentModuleProgress.course_id == course_id
        )
    ).order_by(CourseModule.order_index).all()

    # Calculate statistics
    total_modules = len(progress_records)
    completed = sum(1 for p in progress_records if p.status == 'completed')
    in_progress = sum(1 for p in progress_records if p.status == 'in_progress')
    not_started = sum(1 for p in progress_records if p.status == 'not_started')

    overall_percentage = (completed / total_modules * 100) if total_modules > 0 else 0

    return StudentCourseProgressResponse(
        student_id=student_id,
        course_id=course_id,
        course_name=course.name,
        total_modules=total_modules,
        completed_modules=completed,
        in_progress_modules=in_progress,
        not_started_modules=not_started,
        overall_percentage=round(overall_percentage, 2),
        module_progress=progress_records
    )
