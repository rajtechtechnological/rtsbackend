from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.dependencies import get_current_user, check_resource_access

router = APIRouter()


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new course"""
    # For super_admin, institution_id is optional (global courses)
    # For other roles, use their institution_id or the provided one
    if current_user.role == "super_admin":
        institution_id = course_data.institution_id
    else:
        institution_id = course_data.institution_id or current_user.institution_id
        if institution_id:
            check_resource_access(current_user, institution_id)

    new_course = Course(
        institution_id=institution_id,
        name=course_data.name,
        description=course_data.description,
        duration_months=course_data.duration_months,
        fee_amount=course_data.fee_amount
    )

    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return new_course


@router.get("/", response_model=List[CourseResponse])
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List courses with override logic:
    - Super admin sees all courses
    - Franchise admin sees:
      - All global courses (institution_id IS NULL)
      - Their institution-specific overrides
      - Institution overrides replace global courses with same name
    """
    if current_user.role == "super_admin":
        # Super admin sees everything
        courses = db.query(Course).all()
    else:
        # Get global courses (institution_id is NULL)
        global_courses = db.query(Course).filter(Course.institution_id.is_(None)).all()

        # Get institution-specific courses (overrides)
        institution_courses = db.query(Course).filter(
            Course.institution_id == current_user.institution_id
        ).all()

        # Build a dict of institution courses by name for quick lookup
        institution_course_names = {c.name for c in institution_courses}

        # Combine: institution courses + global courses (excluding overridden ones)
        courses = institution_courses + [
            c for c in global_courses
            if c.name not in institution_course_names
        ]

    return courses


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get course details"""
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    check_resource_access(current_user, course.institution_id)

    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: UUID,
    update_data: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update course details
    - Super admin: updates the course directly
    - Franchise admin editing global course: creates institution-specific override
    - Franchise admin editing own course: updates it directly
    """
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # If course is global (institution_id is NULL) and user is NOT super_admin
    # Create an institution-specific override instead of updating the global course
    if course.institution_id is None and current_user.role != "super_admin":
        # Create a new course as an override for this institution
        override_course = Course(
            institution_id=current_user.institution_id,
            name=course.name,  # Keep same name to link override
            description=course.description,
            duration_months=course.duration_months,
            fee_amount=course.fee_amount
        )

        # Apply the updates to the override
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(override_course, key, value)

        db.add(override_course)
        db.commit()
        db.refresh(override_course)

        return override_course
    else:
        # Normal update flow (super_admin or updating own institution course)
        check_resource_access(current_user, course.institution_id)

        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(course, key, value)

        db.commit()
        db.refresh(course)

        return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a course
    - Super admin: can delete any course (global or institution-specific)
    - Franchise admin: can only delete their own institution's overrides
    - Cannot delete global courses unless super_admin
    """
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # If course is global and user is not super_admin, prevent deletion
    if course.institution_id is None and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete global courses. Only institution-specific overrides can be deleted."
        )

    # Check access for institution-specific courses
    check_resource_access(current_user, course.institution_id)

    db.delete(course)
    db.commit()

    return None
