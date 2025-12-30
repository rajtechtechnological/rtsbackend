from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============ Course Module Schemas ============

class CourseModuleBase(BaseModel):
    module_number: int
    module_name: str
    description: Optional[str] = None
    lesson_count: int = 0
    duration_hours: Optional[int] = None
    total_marks: float = 100
    passing_marks: float = 40
    order_index: int
    has_online_test: bool = False
    test_duration_minutes: Optional[int] = None


class CourseModuleCreate(CourseModuleBase):
    course_id: UUID


class CourseModuleUpdate(BaseModel):
    module_name: Optional[str] = None
    description: Optional[str] = None
    lesson_count: Optional[int] = None
    duration_hours: Optional[int] = None
    total_marks: Optional[float] = None
    passing_marks: Optional[float] = None
    order_index: Optional[int] = None
    has_online_test: Optional[bool] = None
    test_duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class CourseModuleResponse(CourseModuleBase):
    id: UUID
    course_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Student Module Progress Schemas ============

class StudentModuleProgressBase(BaseModel):
    status: str  # not_started, in_progress, completed, failed
    notes: Optional[str] = None


class StudentModuleProgressCreate(BaseModel):
    """For creating initial progress record when student enrolls"""
    student_id: UUID
    course_id: UUID
    module_id: UUID
    enrollment_id: Optional[UUID] = None


class ModuleMarksEntry(BaseModel):
    """For accountants to enter exam marks"""
    student_id: UUID
    module_id: UUID
    marks_obtained: float
    exam_date: Optional[datetime] = None
    notes: Optional[str] = None


class StudentModuleProgressUpdate(BaseModel):
    """For updating progress status"""
    status: Optional[str] = None
    marks_obtained: Optional[float] = None
    exam_date: Optional[datetime] = None
    notes: Optional[str] = None


class StudentModuleProgressResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_id: UUID
    module_id: UUID
    enrollment_id: Optional[UUID] = None
    status: str
    marks_obtained: Optional[float] = None
    exam_date: Optional[datetime] = None
    passed: Optional[bool] = None
    marked_by: Optional[UUID] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Include module info for easy display
    module: Optional[CourseModuleResponse] = None

    class Config:
        from_attributes = True


# ============ Combined Response Schemas ============

class CourseWithModulesResponse(BaseModel):
    """Course with all its modules"""
    id: UUID
    name: str
    description: Optional[str] = None
    duration_months: Optional[int] = None
    fee_amount: Optional[float] = None
    modules: list[CourseModuleResponse] = []

    class Config:
        from_attributes = True


class StudentCourseProgressResponse(BaseModel):
    """Student's progress in a course with all modules"""
    student_id: UUID
    course_id: UUID
    course_name: str
    total_modules: int
    completed_modules: int
    in_progress_modules: int
    not_started_modules: int
    overall_percentage: float
    module_progress: list[StudentModuleProgressResponse] = []


class ModuleProgressSummary(BaseModel):
    """Summary stats for a module"""
    module_id: UUID
    module_name: str
    module_number: int
    total_students_enrolled: int
    students_completed: int
    students_in_progress: int
    students_not_started: int
    average_marks: Optional[float] = None
    pass_rate: Optional[float] = None  # Percentage of students who passed
