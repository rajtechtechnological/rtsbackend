"""
Courses. institution_id NULL = global template (visible to every tenant,
managed by super_admin only). Institutions clone-on-adopt: editing a global
course creates an institution-owned override (copy-on-write — canonical
behavior per docs/01 §1). Writes require staff_manager+.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.dependencies import require_roles, MANAGER_ROLES, ALL_ROLES
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse
from app.tenancy import TenantContext, get_tenant

router = APIRouter()


def _visible_course_or_404(ctx: TenantContext, course_id: UUID) -> Course:
    """A course is visible if it is global or belongs to the caller's
    institution. Anything else is a 404."""
    query = ctx.db.query(Course).filter(Course.id == course_id)
    if ctx.institution_id is not None:
        query = query.filter(
            (Course.institution_id == ctx.institution_id) | (Course.institution_id.is_(None))
        )
    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def create_course(
    course_data: CourseCreate,
    ctx: TenantContext = Depends(get_tenant),
):
    """Create a course. super_admin with no institution_id creates a global
    template; tenant users always create courses owned by their own
    institution (request institution_id is ignored)."""
    if ctx.institution_id is not None:
        institution_id = ctx.institution_id  # never trust the request body
    else:
        institution_id = course_data.institution_id  # None = global template

    new_course = Course(
        institution_id=institution_id,
        name=course_data.name,
        description=course_data.description,
        duration_months=course_data.duration_months,
        fee_amount=course_data.fee_amount,
    )

    ctx.db.add(new_course)
    ctx.db.commit()
    ctx.db.refresh(new_course)
    return new_course


@router.get(
    "/",
    response_model=List[CourseResponse],
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def list_courses(ctx: TenantContext = Depends(get_tenant)):
    """
    List courses with override logic:
    - super_admin sees all courses
    - tenant users see global templates + their institution's overrides;
      an override replaces the global course with the same name.
    """
    if ctx.institution_id is None:
        return ctx.db.query(Course).all()

    global_courses = ctx.db.query(Course).filter(Course.institution_id.is_(None)).all()
    institution_courses = ctx.db.query(Course).filter(
        Course.institution_id == ctx.institution_id
    ).all()

    institution_course_names = {c.name for c in institution_courses}
    return institution_courses + [
        c for c in global_courses if c.name not in institution_course_names
    ]


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_roles(ALL_ROLES))],
)
def get_course(
    course_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    return _visible_course_or_404(ctx, course_id)


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def update_course(
    course_id: UUID,
    update_data: CourseUpdate,
    ctx: TenantContext = Depends(get_tenant),
):
    """
    Update a course:
    - super_admin: updates directly (including global templates)
    - tenant manager editing a GLOBAL course: creates an institution-owned
      override (copy-on-write; shared rows are never edited)
    - tenant manager editing own course: updates it directly
    """
    course = _visible_course_or_404(ctx, course_id)

    if course.institution_id is None and ctx.institution_id is not None:
        override_course = Course(
            institution_id=ctx.institution_id,
            name=course.name,  # same name links override to template
            description=course.description,
            duration_months=course.duration_months,
            fee_amount=course.fee_amount,
        )
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(override_course, key, value)

        ctx.db.add(override_course)
        ctx.db.commit()
        ctx.db.refresh(override_course)
        return override_course

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(course, key, value)

    ctx.db.commit()
    ctx.db.refresh(course)
    return course


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(MANAGER_ROLES))],
)
def delete_course(
    course_id: UUID,
    ctx: TenantContext = Depends(get_tenant),
):
    """Delete a course. Global templates can only be deleted by super_admin;
    tenant managers may delete their own institution's overrides."""
    course = _visible_course_or_404(ctx, course_id)

    if course.institution_id is None and ctx.institution_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete global courses. Only institution-specific overrides can be deleted.",
        )

    ctx.db.delete(course)
    ctx.db.commit()
    return None
