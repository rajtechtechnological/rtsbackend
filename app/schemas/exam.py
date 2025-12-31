from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime, time
from uuid import UUID


# ============ Question Schemas ============

class QuestionBase(BaseModel):
    question_text: str = Field(..., min_length=1)
    option_a: str = Field(..., min_length=1)
    option_b: str = Field(..., min_length=1)
    option_c: str = Field(..., min_length=1)
    option_d: str = Field(..., min_length=1)
    correct_option: str = Field(..., pattern="^[ABCD]$")
    marks: int = Field(default=1, ge=1)
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    order_index: Optional[int] = None


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_option: Optional[str] = Field(None, pattern="^[ABCD]$")
    marks: Optional[int] = Field(None, ge=1)
    explanation: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class QuestionResponse(QuestionBase):
    id: UUID
    exam_id: UUID
    order_index: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionBulkCreate(BaseModel):
    """For bulk importing questions"""
    questions: List[QuestionCreate]


# ============ Exam Schemas ============

class ExamBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    passing_marks: int = Field(default=40, ge=0, le=100)
    duration_minutes: int = Field(default=60, ge=1, le=480)
    allow_retakes: bool = False
    max_retakes: int = Field(default=0, ge=0)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    show_result_immediately: bool = False
    # Batch targeting
    batch_time: Optional[str] = None  # e.g., "9AM-10AM"
    batch_month: Optional[str] = None  # MM format
    batch_year: Optional[str] = None  # YYYY format
    batch_identifier: Optional[str] = None  # "A" or "B"


class ExamCreate(ExamBase):
    course_id: UUID
    module_id: UUID
    batch_time: str  # Required for exam creation
    batch_month: str  # Required
    batch_year: str  # Required
    batch_identifier: Optional[str] = None  # Optional A/B


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    passing_marks: Optional[int] = Field(None, ge=0, le=100)
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    is_active: Optional[bool] = None
    allow_retakes: Optional[bool] = None
    max_retakes: Optional[int] = Field(None, ge=0)
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    show_result_immediately: Optional[bool] = None


class ExamResponse(ExamBase):
    id: UUID
    course_id: UUID
    module_id: UUID
    institution_id: UUID
    total_questions: int
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExamDetailResponse(ExamResponse):
    """Exam with questions for manager view"""
    questions: List[QuestionResponse] = []
    course_name: Optional[str] = None
    module_name: Optional[str] = None


# ============ Exam Schedule Schemas ============

class ExamScheduleBase(BaseModel):
    batch_time: str  # e.g., "9AM-10AM"
    batch_identifier: Optional[str] = None  # 'A' or 'B'
    batch_month: Optional[str] = None  # MM format
    batch_year: Optional[str] = None  # YYYY format
    scheduled_date: date
    start_time: time
    end_time: time


class ExamScheduleCreate(ExamScheduleBase):
    exam_id: UUID


class ExamScheduleResponse(ExamScheduleBase):
    id: UUID
    exam_id: UUID
    institution_id: UUID
    is_active: bool
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ExamScheduleDetailResponse(ExamScheduleResponse):
    """Schedule with exam info"""
    exam_title: Optional[str] = None
    course_name: Optional[str] = None
    module_name: Optional[str] = None


# ============ Student Answer Schemas ============

class AnswerSubmit(BaseModel):
    """For submitting/saving an answer"""
    question_id: UUID
    selected_option: Optional[str] = Field(None, pattern="^[ABCD]$")
    marked_for_review: bool = False


class StudentAnswerResponse(BaseModel):
    id: UUID
    question_id: UUID
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
    marks_obtained: int
    marked_for_review: bool
    answered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Exam Attempt Schemas ============

class ExamAttemptStart(BaseModel):
    """Response when starting an exam"""
    attempt_id: UUID
    exam_id: UUID
    exam_title: str
    duration_minutes: int
    total_questions: int
    start_time: datetime
    end_time: datetime  # Calculated: start_time + duration
    questions: List[Dict[str, Any]]  # Shuffled questions without correct answers


class ExamAttemptState(BaseModel):
    """Current state of an in-progress exam"""
    attempt_id: UUID
    exam_id: UUID
    exam_title: str
    status: str
    current_question_index: int
    total_questions: int
    time_remaining_seconds: int
    answers: Dict[str, Optional[str]]  # question_id -> selected_option
    marked_for_review: List[str]  # List of question_ids marked for review


class ExamAttemptResponse(BaseModel):
    id: UUID
    exam_id: UUID
    student_id: UUID
    attempt_number: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_marks: Optional[int] = None
    obtained_marks: Optional[int] = None
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    total_answered: int
    correct_answers: Optional[int] = None
    is_verified: bool
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExamAttemptDetailResponse(ExamAttemptResponse):
    """Detailed attempt with answers for verification"""
    exam_title: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    answers: List[StudentAnswerResponse] = []


# ============ Exam Result Schemas ============

class ExamResultResponse(BaseModel):
    """Result shown to student after verification"""
    attempt_id: UUID
    exam_id: UUID
    exam_title: str
    course_name: str
    module_name: str
    attempt_number: int
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_taken_minutes: Optional[int] = None
    total_questions: int
    total_answered: int
    correct_answers: int
    total_marks: int
    obtained_marks: int
    percentage: float
    passed: bool
    is_verified: bool
    verified_at: Optional[datetime] = None


# ============ Verification Schemas ============

class ExamVerifyRequest(BaseModel):
    """Request to verify an exam attempt"""
    notes: Optional[str] = None


class RetakeAllowRequest(BaseModel):
    """Request to allow a retake"""
    notes: Optional[str] = None


# ============ Student Exam List Schemas ============

class AvailableExamResponse(BaseModel):
    """Exam available for student to take"""
    exam_id: UUID
    exam_title: str
    course_id: UUID
    course_name: str
    module_id: UUID
    module_name: str
    total_questions: int
    duration_minutes: int
    passing_marks: int
    is_locked: bool
    lock_reason: Optional[str] = None  # e.g., "Payment pending", "Not scheduled"
    schedule_id: Optional[UUID] = None
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    previous_attempts: int
    can_retake: bool
    best_score: Optional[float] = None


class StudentExamHistoryResponse(BaseModel):
    """Student's exam attempt history"""
    exam_id: UUID
    exam_title: str
    course_name: str
    module_name: str
    attempts: List[ExamAttemptResponse]
