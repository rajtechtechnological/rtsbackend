from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.course import Course
from app.models.course_module import CourseModule, StudentModuleProgress
from app.models.student import Student
from app.models.student_course import StudentCourse
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

router = APIRouter()


# ============ COURSE MODULE MANAGEMENT ============

@router.post("/courses/{course_id}/modules", response_model=CourseModuleResponse)
def create_course_module(
    course_id: UUID,
    module_data: CourseModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new module for a course.
    Only institution_director, staff_manager, or super_admin can create modules.
    """
    if current_user.role not in ["institution_director", "staff_manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to create modules")

    # Verify course exists and user has access
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Verify module number is unique for this course
    existing_module = db.query(CourseModule).filter(
        and_(
            CourseModule.course_id == course_id,
            CourseModule.module_number == module_data.module_number
        )
    ).first()
    if existing_module:
        raise HTTPException(
            status_code=400,
            detail=f"Module number {module_data.module_number} already exists for this course"
        )

    # Create module
    new_module = CourseModule(**module_data.dict())
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module


@router.get("/courses/{course_id}/modules", response_model=List[CourseModuleResponse])
def get_course_modules(
    course_id: UUID,
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all modules for a course, ordered by order_index"""
    # Verify course exists and user has access
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(CourseModule).filter(CourseModule.course_id == course_id)

    if not include_inactive:
        query = query.filter(CourseModule.is_active == True)

    modules = query.order_by(CourseModule.order_index).all()
    return modules


@router.get("/courses/{course_id}/with-modules", response_model=CourseWithModulesResponse)
def get_course_with_modules(
    course_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get course details with all its modules"""
    course = db.query(Course).options(
        joinedload(Course.modules)
    ).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return course


@router.get("/modules/{module_id}", response_model=CourseModuleResponse)
def get_module(
    module_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific module by ID"""
    module = db.query(CourseModule).options(
        joinedload(CourseModule.course)
    ).filter(CourseModule.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if module.course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return module


@router.patch("/modules/{module_id}", response_model=CourseModuleResponse)
def update_module(
    module_id: UUID,
    module_data: CourseModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a module. Only directors/managers can update."""
    if current_user.role not in ["institution_director", "staff_manager", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to update modules")

    module = db.query(CourseModule).options(
        joinedload(CourseModule.course)
    ).filter(CourseModule.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if module.course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    update_data = module_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    db.commit()
    db.refresh(module)
    return module


@router.delete("/modules/{module_id}")
def delete_module(
    module_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a module. Only directors/super_admin can delete."""
    if current_user.role not in ["institution_director", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete modules")

    module = db.query(CourseModule).options(
        joinedload(CourseModule.course)
    ).filter(CourseModule.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if module.course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    db.delete(module)
    db.commit()
    return {"message": "Module deleted successfully"}


# ============ STUDENT MODULE PROGRESS ============

@router.post("/students/{student_id}/progress", response_model=StudentModuleProgressResponse)
def create_student_progress(
    student_id: UUID,
    progress_data: StudentModuleProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create initial progress record for a student when they enroll in a course.
    This creates progress entries for all modules in the course.
    """
    if current_user.role not in ["institution_director", "staff_manager", "accountant", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify student exists and user has access
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Verify module exists
    module = db.query(CourseModule).filter(CourseModule.id == progress_data.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Check if progress already exists
    existing_progress = db.query(StudentModuleProgress).filter(
        and_(
            StudentModuleProgress.student_id == student_id,
            StudentModuleProgress.module_id == progress_data.module_id
        )
    ).first()

    if existing_progress:
        raise HTTPException(
            status_code=400,
            detail="Progress record already exists for this student and module"
        )

    # Create progress record
    new_progress = StudentModuleProgress(**progress_data.dict())
    db.add(new_progress)
    db.commit()
    db.refresh(new_progress)

    # Load relationships for response
    db.refresh(new_progress)
    new_progress = db.query(StudentModuleProgress).options(
        joinedload(StudentModuleProgress.module)
    ).filter(StudentModuleProgress.id == new_progress.id).first()

    return new_progress


@router.post("/students/{student_id}/courses/{course_id}/initialize-progress")
def initialize_student_course_progress(
    student_id: UUID,
    course_id: UUID,
    enrollment_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize progress records for all modules in a course when student enrolls.
    This is typically called automatically when a student enrolls in a course.
    """
    if current_user.role not in ["institution_director", "staff_manager", "accountant", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify student exists
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get all modules for the course
    modules = db.query(CourseModule).filter(
        and_(
            CourseModule.course_id == course_id,
            CourseModule.is_active == True
        )
    ).order_by(CourseModule.order_index).all()

    if not modules:
        raise HTTPException(status_code=404, detail="No modules found for this course")

    created_count = 0
    for module in modules:
        # Check if progress already exists
        existing = db.query(StudentModuleProgress).filter(
            and_(
                StudentModuleProgress.student_id == student_id,
                StudentModuleProgress.module_id == module.id
            )
        ).first()

        if not existing:
            progress = StudentModuleProgress(
                student_id=student_id,
                course_id=course_id,
                module_id=module.id,
                enrollment_id=enrollment_id,
                status='not_started'
            )
            db.add(progress)
            created_count += 1

    db.commit()

    return {
        "message": f"Initialized progress for {created_count} modules",
        "total_modules": len(modules),
        "created": created_count
    }


@router.get("/students/{student_id}/courses/{course_id}/progress", response_model=StudentCourseProgressResponse)
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


@router.get("/students/{student_id}/progress", response_model=List[StudentModuleProgressResponse])
def get_student_all_progress(
    student_id: UUID,
    course_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all progress records for a student, optionally filtered by course"""
    # Verify student exists
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Permission check
    if current_user.role == "student":
        if student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only view your own progress")
    elif current_user.role != "super_admin":
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(StudentModuleProgress).options(
        joinedload(StudentModuleProgress.module)
    ).filter(StudentModuleProgress.student_id == student_id)

    if course_id:
        query = query.filter(StudentModuleProgress.course_id == course_id)

    progress = query.all()
    return progress


@router.patch("/progress/{progress_id}", response_model=StudentModuleProgressResponse)
def update_progress(
    progress_id: UUID,
    progress_data: StudentModuleProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update progress status. Used for manual status updates."""
    if current_user.role not in ["institution_director", "staff_manager", "accountant", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    progress = db.query(StudentModuleProgress).options(
        joinedload(StudentModuleProgress.student),
        joinedload(StudentModuleProgress.module)
    ).filter(StudentModuleProgress.id == progress_id).first()

    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if progress.student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    update_data = progress_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(progress, field, value)

    # Auto-update timestamps based on status
    if progress_data.status == 'in_progress' and not progress.started_at:
        progress.started_at = datetime.utcnow()
    elif progress_data.status == 'completed' and not progress.completed_at:
        progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)
    return progress


# ============ MARKS ENTRY (ACCOUNTANT FUNCTION) ============

@router.post("/progress/enter-marks", response_model=StudentModuleProgressResponse)
def enter_module_marks(
    marks_data: ModuleMarksEntry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accountants enter exam marks for a student's module.
    This automatically calculates pass/fail and updates status.
    """
    if current_user.role not in ["accountant", "staff_manager", "institution_director", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to enter marks")

    # Verify student exists
    student = db.query(Student).filter(Student.id == marks_data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if student.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get module to check passing marks
    module = db.query(CourseModule).filter(CourseModule.id == marks_data.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Validate marks
    if marks_data.marks_obtained < 0 or marks_data.marks_obtained > module.total_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Marks must be between 0 and {module.total_marks}"
        )

    # Find progress record
    progress = db.query(StudentModuleProgress).filter(
        and_(
            StudentModuleProgress.student_id == marks_data.student_id,
            StudentModuleProgress.module_id == marks_data.module_id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=404,
            detail="Progress record not found. Student may not be enrolled in this module."
        )

    # Calculate pass/fail
    passed = marks_data.marks_obtained >= module.passing_marks

    # Update progress
    progress.marks_obtained = marks_data.marks_obtained
    progress.exam_date = marks_data.exam_date or datetime.utcnow()
    progress.passed = passed
    progress.status = 'completed' if passed else 'failed'
    progress.marked_by = current_user.id
    progress.notes = marks_data.notes
    progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)

    # Load relationships
    progress = db.query(StudentModuleProgress).options(
        joinedload(StudentModuleProgress.module)
    ).filter(StudentModuleProgress.id == progress.id).first()

    return progress


# ============ MODULE ANALYTICS & SUMMARY ============

@router.get("/modules/{module_id}/progress", response_model=List[StudentModuleProgressResponse])
def get_module_progress(
    module_id: UUID,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all student progress records for a specific module"""
    if current_user.role not in ["institution_director", "staff_manager", "accountant", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify module exists
    module = db.query(CourseModule).options(
        joinedload(CourseModule.course)
    ).filter(CourseModule.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if module.course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(StudentModuleProgress).options(
        joinedload(StudentModuleProgress.student).joinedload(Student.user),
        joinedload(StudentModuleProgress.module)
    ).filter(StudentModuleProgress.module_id == module_id)

    if status:
        query = query.filter(StudentModuleProgress.status == status)

    progress = query.all()
    return progress


@router.get("/modules/{module_id}/summary", response_model=ModuleProgressSummary)
def get_module_summary(
    module_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistical summary for a module (total enrolled, completed, pass rate, etc.)"""
    if current_user.role not in ["institution_director", "staff_manager", "accountant", "super_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify module exists
    module = db.query(CourseModule).options(
        joinedload(CourseModule.course)
    ).filter(CourseModule.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Multi-tenant check
    if current_user.role != "super_admin":
        if module.course.institution_id != current_user.institution_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get all progress records for this module
    progress_records = db.query(StudentModuleProgress).filter(
        StudentModuleProgress.module_id == module_id
    ).all()

    total_enrolled = len(progress_records)
    completed = sum(1 for p in progress_records if p.status == 'completed')
    in_progress = sum(1 for p in progress_records if p.status == 'in_progress')
    not_started = sum(1 for p in progress_records if p.status == 'not_started')

    # Calculate average marks (only for students who have taken the exam)
    marks_list = [p.marks_obtained for p in progress_records if p.marks_obtained is not None]
    average_marks = sum(marks_list) / len(marks_list) if marks_list else None

    # Calculate pass rate
    passed_count = sum(1 for p in progress_records if p.passed == True)
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
        pass_rate=round(pass_rate, 2) if pass_rate else None
    )
