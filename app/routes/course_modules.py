"""
Course modules + student module progress. Modules carry no institution_id —
they are scoped through their parent course (own institution or global
template). Managing modules and entering marks requires staff_manager+
(the old 'accountant' role is folded into staff_manager, docs/01 §3);
students may view their own progress only.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.dependencies import require_roles, MANAGER_ROLES, STAFF_ADMIN_ROLES, STUDENT_MANAGER_ROLES, ALL_ROLES
from app.models.course import Course
from app.models.course_module import CourseModule, StudentModuleProgress
from app.models.student import Student
from app.schemas.course_module import (
    CourseModuleCreate,
    CourseModuleUpdate,
    CourseModuleResponse,
    StudentModuleProgressCreate,
    StudentModuleProgressUpdate,
    StudentModuleProgressResponse,
    ModuleMarksEntry,
    CourseWithModulesResponse,
    StudentCourseProgressResponse,
    ModuleProgressSummary,
)
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _visible_course_or_404(ctx: TenantContext, course_id: UUID) -> Course:
    """Own institution's course or a global template; anything else 404s."""
    query = ctx.db.query(Course).filter(Course.id == course_id)
    if ctx.institution_id is not None:
        query = query.filter(
            (Course.institution_id == ctx.institution_id) | (Course.institution_id.is_(None))
        )
    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _visible_module_or_404(ctx: TenantContext, module_id: UUID) -> CourseModule:
    module = (
        ctx.db.query(CourseModule)
        .options(joinedload(CourseModule.course))
        .filter(CourseModule.id == module_id)
        .first()
    )
    if not module or (
        ctx.institution_id is not None
        and module.course.institution_id is not None
        and module.course.institution_id != ctx.institution_id
    ):
        raise HTTPException(status_code=404, detail="Module not found")
    return module


def _scoped_student_or_404(ctx: TenantContext, student_id: UUID) -> Student:
    student = ctx.q(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _student_readable_or_404(ctx: TenantContext, student_id: UUID) -> Student:
    """Staff read any student in their institution; students only themselves."""
    student = _scoped_student_or_404(ctx, student_id)
    if ctx.user.role == "student" and student.user_id != ctx.user.id:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# ============ COURSE MODULE MANAGEMENT ============

@router.post(
    "/courses/{course_id}/modules",
    response_model=CourseModuleResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def create_course_module(
    course_id: UUID,
    module_data: CourseModuleCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Create a module (staff_manager+). Tenant managers can only add modules
    to their own institution's courses (global templates are super_admin's)."""
    course = _visible_course_or_404(ctx, course_id)

    if course.institution_id is None and ctx.institution_id is not None:
        raise HTTPException(
            status_code=403,
            detail="Global course templates are managed by head office; edit the course to create your institution's copy first",
        )

    existing_module = ctx.db.query(CourseModule).filter(
        and_(
            CourseModule.course_id == course.id,
            CourseModule.module_number == module_data.module_number,
        )
    ).first()
    if existing_module:
        raise HTTPException(
            status_code=400,
            detail=f"Module number {module_data.module_number} already exists for this course",
        )

    new_module = CourseModule(**module_data.model_dump())
    ctx.db.add(new_module)
    ctx.db.commit()
    ctx.db.refresh(new_module)
    return new_module


@router.get(
    "/courses/{course_id}/modules",
    response_model=List[CourseModuleResponse],
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_course_modules(
    course_id: UUID,
    include_inactive: bool = Query(False),
    ctx: TenantContext = Depends(get_tenant),
):
    """All modules for a course, ordered by order_index."""
    course = _visible_course_or_404(ctx, course_id)

    query = ctx.db.query(CourseModule).filter(CourseModule.course_id == course.id)
    if not include_inactive:
        query = query.filter(CourseModule.is_active == True)  # noqa: E712

    return query.order_by(CourseModule.order_index).all()


@router.get(
    "/courses/{course_id}/with-modules",
    response_model=CourseWithModulesResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_course_with_modules(
    course_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    course = _visible_course_or_404(ctx, course_id)
    return (
        ctx.db.query(Course)
        .options(joinedload(Course.modules))
        .filter(Course.id == course.id)
        .first()
    )


@router.get(
    "/modules/{module_id}",
    response_model=CourseModuleResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_module(
    module_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _visible_module_or_404(ctx, module_id)


@router.patch(
    "/modules/{module_id}",
    response_model=CourseModuleResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def update_module(
    module_id: UUID,
    module_data: CourseModuleUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Update a module (staff_manager+, own institution's courses only)."""
    module = _visible_module_or_404(ctx, module_id)
    if module.course.institution_id is None and ctx.institution_id is not None:
        raise HTTPException(status_code=403, detail="Global course templates are managed by head office")

    for field, value in module_data.model_dump(exclude_unset=True).items():
        setattr(module, field, value)

    ctx.db.commit()
    ctx.db.refresh(module)
    return module


@router.delete(
    "/modules/{module_id}",
    dependencies=[Depends(require_roles(STAFF_ADMIN_ROLES))],
)
def delete_module(
    module_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Delete a module (director+, own institution's courses only)."""
    module = _visible_module_or_404(ctx, module_id)
    if module.course.institution_id is None and ctx.institution_id is not None:
        raise HTTPException(status_code=403, detail="Global course templates are managed by head office")

    ctx.db.delete(module)
    ctx.db.commit()
    return {"message": "Module deleted successfully"}


# ============ STUDENT MODULE PROGRESS ============

@router.post(
    "/students/{student_id}/progress",
    response_model=StudentModuleProgressResponse,
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def create_student_progress(
    student_id: UUID,
    progress_data: StudentModuleProgressCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Create a progress record for one module."""
    student = _scoped_student_or_404(ctx, student_id)

    module = _visible_module_or_404(ctx, progress_data.module_id)

    existing_progress = ctx.db.query(StudentModuleProgress).filter(
        and_(
            StudentModuleProgress.student_id == student.id,
            StudentModuleProgress.module_id == module.id,
        )
    ).first()
    if existing_progress:
        raise HTTPException(
            status_code=400,
            detail="Progress record already exists for this student and module",
        )

    new_progress = StudentModuleProgress(**progress_data.model_dump())
    ctx.db.add(new_progress)
    ctx.db.commit()

    return (
        ctx.db.query(StudentModuleProgress)
        .options(joinedload(StudentModuleProgress.module))
        .filter(StudentModuleProgress.id == new_progress.id)
        .first()
    )


@router.post(
    "/students/{student_id}/courses/{course_id}/initialize-progress",
    dependencies=[Depends(require_roles(STUDENT_MANAGER_ROLES))],
)
def initialize_student_course_progress(
    student_id: UUID,
    course_id: UUID,
    enrollment_id: Optional[UUID] = None,
    ctx: TenantContext = Depends(get_tenant),
):
    """Initialize progress records for all modules in a course."""
    student = _scoped_student_or_404(ctx, student_id)
    course = _visible_course_or_404(ctx, course_id)

    modules = ctx.db.query(CourseModule).filter(
        and_(
            CourseModule.course_id == course.id,
            CourseModule.is_active == True,  # noqa: E712
        )
    ).order_by(CourseModule.order_index).all()

    if not modules:
        raise HTTPException(status_code=404, detail="No modules found for this course")

    created_count = 0
    for module in modules:
        existing = ctx.db.query(StudentModuleProgress).filter(
            and_(
                StudentModuleProgress.student_id == student.id,
                StudentModuleProgress.module_id == module.id,
            )
        ).first()
        if not existing:
            ctx.db.add(StudentModuleProgress(
                student_id=student.id,
                course_id=course.id,
                module_id=module.id,
                enrollment_id=enrollment_id,
                status='not_started',
            ))
            created_count += 1

    ctx.db.commit()

    return {
        "message": f"Initialized progress for {created_count} modules",
        "total_modules": len(modules),
        "created": created_count,
    }


@router.get(
    "/students/{student_id}/courses/{course_id}/progress",
    response_model=StudentCourseProgressResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_student_course_progress(
    student_id: UUID,
    course_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Detailed progress for a student in a course (students: own only)."""
    student = _student_readable_or_404(ctx, student_id)
    course = _visible_course_or_404(ctx, course_id)

    progress_records = (
        ctx.db.query(StudentModuleProgress)
        .join(CourseModule, StudentModuleProgress.module_id == CourseModule.id)
        .options(joinedload(StudentModuleProgress.module))
        .filter(
            and_(
                StudentModuleProgress.student_id == student.id,
                StudentModuleProgress.course_id == course.id,
            )
        )
        .order_by(CourseModule.order_index)
        .all()
    )

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
        module_progress=progress_records,
    )


@router.get(
    "/students/{student_id}/progress",
    response_model=List[StudentModuleProgressResponse],
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_student_all_progress(
    student_id: UUID,
    course_id: Optional[UUID] = Query(None),
    ctx: TenantContext = Depends(get_tenant),
):
    """All progress records for a student (students: own only)."""
    student = _student_readable_or_404(ctx, student_id)

    query = (
        ctx.db.query(StudentModuleProgress)
        .options(joinedload(StudentModuleProgress.module))
        .filter(StudentModuleProgress.student_id == student.id)
    )
    if course_id:
        query = query.filter(StudentModuleProgress.course_id == course_id)

    return query.all()


@router.patch(
    "/progress/{progress_id}",
    response_model=StudentModuleProgressResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def update_progress(
    progress_id: UUID,
    progress_data: StudentModuleProgressUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Manual progress status update (staff_manager+)."""
    progress = (
        ctx.db.query(StudentModuleProgress)
        .join(Student, StudentModuleProgress.student_id == Student.id)
        .options(
            joinedload(StudentModuleProgress.student),
            joinedload(StudentModuleProgress.module),
        )
        .filter(StudentModuleProgress.id == progress_id)
    )
    if ctx.institution_id is not None:
        progress = progress.filter(Student.institution_id == ctx.institution_id)
    progress = progress.first()
    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")

    for field, value in progress_data.model_dump(exclude_unset=True).items():
        setattr(progress, field, value)

    if progress_data.status == 'in_progress' and not progress.started_at:
        progress.started_at = datetime.now(timezone.utc)
    elif progress_data.status == 'completed' and not progress.completed_at:
        progress.completed_at = datetime.now(timezone.utc)

    ctx.db.commit()
    ctx.db.refresh(progress)
    return progress


# ============ MARKS ENTRY ============

@router.post(
    "/progress/enter-marks",
    response_model=StudentModuleProgressResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def enter_module_marks(
    marks_data: ModuleMarksEntry,
    ctx: TenantContext = Depends(get_tenant),
):
    """Enter exam marks for a student's module (staff_manager+ — the former
    'accountant' duty). Auto-calculates pass/fail."""
    student = _scoped_student_or_404(ctx, marks_data.student_id)
    module = _visible_module_or_404(ctx, marks_data.module_id)

    if marks_data.marks_obtained < 0 or marks_data.marks_obtained > module.total_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Marks must be between 0 and {module.total_marks}",
        )

    progress = ctx.db.query(StudentModuleProgress).filter(
        and_(
            StudentModuleProgress.student_id == student.id,
            StudentModuleProgress.module_id == module.id,
        )
    ).first()
    if not progress:
        raise HTTPException(
            status_code=404,
            detail="Progress record not found. Student may not be enrolled in this module.",
        )

    passed = marks_data.marks_obtained >= module.passing_marks

    progress.marks_obtained = marks_data.marks_obtained
    progress.exam_date = marks_data.exam_date or datetime.now(timezone.utc)
    progress.passed = passed
    progress.status = 'completed' if passed else 'failed'
    progress.marked_by = ctx.user.id
    progress.notes = marks_data.notes
    progress.completed_at = datetime.now(timezone.utc)

    ctx.db.commit()

    return (
        ctx.db.query(StudentModuleProgress)
        .options(joinedload(StudentModuleProgress.module))
        .filter(StudentModuleProgress.id == progress.id)
        .first()
    )


# ============ MODULE ANALYTICS & SUMMARY ============

@router.get(
    "/modules/{module_id}/progress",
    response_model=List[StudentModuleProgressResponse],
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def get_module_progress(
    module_id: UUID,
    status: Optional[str] = Query(None),
    ctx: TenantContext = Depends(get_tenant),
):
    """All student progress records for a module (staff_manager+)."""
    module = _visible_module_or_404(ctx, module_id)

    query = (
        ctx.db.query(StudentModuleProgress)
        .join(Student, StudentModuleProgress.student_id == Student.id)
        .options(
            joinedload(StudentModuleProgress.student).joinedload(Student.user),
            joinedload(StudentModuleProgress.module),
        )
        .filter(StudentModuleProgress.module_id == module.id)
    )
    # Global modules are shared: only ever show the caller's own students
    if ctx.institution_id is not None:
        query = query.filter(Student.institution_id == ctx.institution_id)
    if status:
        query = query.filter(StudentModuleProgress.status == status)

    return query.all()


@router.get(
    "/modules/{module_id}/summary",
    response_model=ModuleProgressSummary,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def get_module_summary(
    module_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Statistical summary for a module (staff_manager+)."""
    module = _visible_module_or_404(ctx, module_id)

    query = (
        ctx.db.query(StudentModuleProgress)
        .join(Student, StudentModuleProgress.student_id == Student.id)
        .filter(StudentModuleProgress.module_id == module.id)
    )
    if ctx.institution_id is not None:
        query = query.filter(Student.institution_id == ctx.institution_id)
    progress_records = query.all()

    total_enrolled = len(progress_records)
    completed = sum(1 for p in progress_records if p.status == 'completed')
    in_progress = sum(1 for p in progress_records if p.status == 'in_progress')
    not_started = sum(1 for p in progress_records if p.status == 'not_started')

    marks_list = [p.marks_obtained for p in progress_records if p.marks_obtained is not None]
    average_marks = sum(marks_list) / len(marks_list) if marks_list else None

    passed_count = sum(1 for p in progress_records if p.passed == True)  # noqa: E712
    total_attempted = sum(1 for p in progress_records if p.marks_obtained is not None)
    pass_rate = (passed_count / total_attempted * 100) if total_attempted > 0 else None

    return ModuleProgressSummary(
        module_id=module_id,
        module_name=module.module_name,
        module_number=module.module_number,
        total_students_enrolled=total_enrolled,
        students_completed=completed,
        students_in_progress=in_progress,
        students_not_started=not_started,
        average_marks=round(average_marks, 2) if average_marks else None,
        pass_rate=round(pass_rate, 2) if pass_rate else None,
    )
