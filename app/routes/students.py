"""
Student management. All queries go through TenantContext (docs/01 §4);
institution_id is never accepted from request bodies. Human-readable student
IDs come from the atomic id_counters helper (docs/02 §6).
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import joinedload
from typing import List
from uuid import UUID
from datetime import datetime

from app import ids
from app.dependencies import require_roles, ALL_STAFF_ROLES, STUDENT_MANAGER_ROLES
from app.models.batch import Batch
from app.models.course import Course
from app.models.course_module import CourseModule, StudentModuleProgress
from app.models.institution import Institution
from app.models.student import Student
from app.models.student_course import StudentCourse
from app.models.user import User
from app.schemas.course_module import StudentCourseProgressResponse
from app.schemas.student import (
    StudentCreate, StudentRegister, StudentUpdate,
    StudentListItem, StudentResponse, CourseEnrollmentCreate,
)
from app.services.auth_service import hash_password
from app.services.storage_service import storage
from app.tenancy import TenantContext, get_tenant
from sqlalchemy import and_

router = APIRouter()


def _get_student_or_404(ctx: TenantContext, student_pk: UUID) -> Student:
    """Fetch a student inside the tenant scope; out-of-tenant rows 404."""
    student = (
        ctx.q(Student)
        .options(joinedload(Student.user), joinedload(Student.course_enrollments))
        .filter(Student.id == student_pk)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _get_batch_or_400(ctx: TenantContext, institution_id: UUID, batch_id: UUID) -> Batch:
    batch = ctx.db.query(Batch).filter(
        Batch.id == batch_id,
        Batch.institution_id == institution_id,
    ).first()
    if not batch:
        raise HTTPException(status_code=400, detail="Batch not found in this institution")
    return batch


def _generate_student_id(ctx: TenantContext, institution_id: UUID) -> str:
    institution = ctx.db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    now = datetime.now()
    return ids.student_id(ctx.db, institution, now.month, now.year)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def create_student(
    student_data: StudentCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Create a student profile for an existing user (receptionist+)."""
    institution_id = ctx.require_institution_id()
    _get_batch_or_400(ctx, institution_id, student_data.batch_id)

    new_student = Student(
        user_id=student_data.user_id,
        institution_id=institution_id,
        batch_id=student_data.batch_id,
        student_id=_generate_student_id(ctx, institution_id),
        date_of_birth=student_data.date_of_birth,
        father_name=student_data.father_name,
        guardian_name=student_data.guardian_name,
        guardian_phone=student_data.guardian_phone,
        address=student_data.address,
        aadhar_number=student_data.aadhar_number,
        apaar_id=student_data.apaar_id,
        last_qualification=student_data.last_qualification,
    )

    ctx.db.add(new_student)
    ctx.db.commit()
    ctx.db.refresh(new_student)
    return new_student


@router.post(
    "/register",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def register_student(
    data: StudentRegister,
    ctx: TenantContext = Depends(get_tenant),
):
    """
    Register a new student (creates user + student in one call).
    Student accounts are created by staff — no self-signup (docs/01 §5).
    """
    institution_id = ctx.require_institution_id()
    _get_batch_or_400(ctx, institution_id, data.batch_id)

    existing_user = ctx.db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    default_password = data.phone if data.phone else "student123"
    new_user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        hashed_password=hash_password(default_password),
        role="student",
        institution_id=institution_id,
        is_active=True,
    )
    ctx.db.add(new_user)
    ctx.db.flush()

    new_student = Student(
        user_id=new_user.id,
        institution_id=institution_id,
        batch_id=data.batch_id,
        student_id=_generate_student_id(ctx, institution_id),
        date_of_birth=data.date_of_birth,
        father_name=data.father_name,
        guardian_name=data.guardian_name,
        guardian_phone=data.guardian_phone,
        address=data.address,
        aadhar_number=data.aadhar_number,
        apaar_id=data.apaar_id,
        last_qualification=data.last_qualification,
    )
    ctx.db.add(new_student)
    ctx.db.flush()

    if data.course_id:
        course = ctx.db.query(Course).filter(
            Course.id == data.course_id,
            (Course.institution_id == institution_id) | (Course.institution_id.is_(None)),
        ).first()
        if course:
            ctx.db.add(StudentCourse(student_id=new_student.id, course_id=course.id))

    ctx.db.commit()
    ctx.db.refresh(new_student)
    return new_student


@router.get(
    "/",
    response_model=List[StudentListItem],
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def list_students(ctx: TenantContext = Depends(get_tenant)):
    """List students in the caller's institution (no aadhar in list shape)."""
    return (
        ctx.q(Student)
        .options(joinedload(Student.user), joinedload(Student.course_enrollments))
        .all()
    )


@router.get(
    "/search",
    response_model=StudentResponse,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def search_student_by_id(
    student_id: str,
    ctx: TenantContext = Depends(get_tenant),
):
    """Search by human-readable ID (e.g. RTS-NAL-RCC-12-2025-0001)."""
    student = (
        ctx.q(Student)
        .options(joinedload(Student.user))
        .filter(Student.student_id == student_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found with this ID")
    return student


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def get_student(
    student_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Single-student detail (includes aadhar — receptionist+ only, docs/02)."""
    return _get_student_or_404(ctx, student_id)


@router.patch(
    "/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def update_student(
    student_id: UUID,
    update_data: StudentUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    student = _get_student_or_404(ctx, student_id)

    update_dict = update_data.model_dump(exclude_unset=True)

    if "student_id" in update_dict and update_dict["student_id"] != student.student_id:
        existing = ctx.db.query(Student).filter(
            Student.student_id == update_dict["student_id"],
            Student.id != student_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Student ID '{update_dict['student_id']}' already exists.",
            )

    if "batch_id" in update_dict and update_dict["batch_id"] is not None:
        _get_batch_or_400(ctx, student.institution_id, update_dict["batch_id"])

    if "status" in update_dict and update_dict["status"] not in ("active", "completed", "dropped", None):
        raise HTTPException(status_code=400, detail="Invalid status")

    for key, value in update_dict.items():
        setattr(student, key, value)

    ctx.db.commit()
    ctx.db.refresh(student)
    return student


@router.post(
    "/{student_id}/photo",
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def upload_student_photo(
    student_id: UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(get_tenant),
):
    student = _get_student_or_404(ctx, student_id)

    file_url = storage.upload_file(file.file, "photos", file.filename)
    student.photo_url = file_url

    ctx.db.commit()
    return {"photo_url": file_url}


@router.post(
    "/{student_id}/enroll",
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def enroll_in_course(
    student_id: UUID,
    enrollment: CourseEnrollmentCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    student = _get_student_or_404(ctx, student_id)

    course = ctx.db.query(Course).filter(
        Course.id == enrollment.course_id,
        (Course.institution_id == student.institution_id) | (Course.institution_id.is_(None)),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = ctx.db.query(StudentCourse).filter(
        StudentCourse.student_id == student.id,
        StudentCourse.course_id == course.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    ctx.db.add(StudentCourse(student_id=student.id, course_id=course.id))
    ctx.db.commit()
    return {"message": "Enrolled successfully"}


@router.get(
    "/{student_id}/courses",
    dependencies=[Depends(require_roles(ALL_STAFF_ROLES))],
)
def get_student_courses(
    student_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    student = _get_student_or_404(ctx, student_id)
    return (
        ctx.db.query(StudentCourse)
        .options(joinedload(StudentCourse.course))
        .filter(StudentCourse.student_id == student.id)
        .all()
    )


@router.get("/{student_id}/courses/{course_id}/progress", response_model=StudentCourseProgressResponse)
def get_student_course_progress(
    student_id: UUID,
    course_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Progress for a student in a course. Students may only see their own."""
    student = _get_student_or_404(ctx, student_id)

    if ctx.user.role == "student" and student.user_id != ctx.user.id:
        # Own-records-only: someone else's student row is a 404 for students.
        raise HTTPException(status_code=404, detail="Student not found")

    course = ctx.db.query(Course).filter(
        Course.id == course_id,
        (Course.institution_id == student.institution_id) | (Course.institution_id.is_(None)),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    progress_records = (
        ctx.db.query(StudentModuleProgress)
        .join(CourseModule, StudentModuleProgress.module_id == CourseModule.id)
        .options(joinedload(StudentModuleProgress.module))
        .filter(
            and_(
                StudentModuleProgress.student_id == student.id,
                StudentModuleProgress.course_id == course_id,
            )
        )
        .order_by(CourseModule.order_index)
        .all()
    )

    total_modules = len(progress_records)
    completed = sum(1 for p in progress_records if p.status == "completed")
    in_progress = sum(1 for p in progress_records if p.status == "in_progress")
    not_started = sum(1 for p in progress_records if p.status == "not_started")
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
        module_progress=progress_records,
    )
