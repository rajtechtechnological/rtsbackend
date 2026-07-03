from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Time, ForeignKey, Boolean,
    Text, JSON, CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Exam(Base):
    """
    Exam configuration for a course module. Always institution-owned (F-04):
    creation requires an owning institution — super_admin must pick one.
    Batch targeting lives ONLY on exam_schedules (F-08).
    """
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Exam details
    title = Column(String, nullable=False)
    description = Column(Text)
    total_questions = Column(Integer, nullable=False, default=0)
    passing_marks = Column(Integer, nullable=False, default=40)
    duration_minutes = Column(Integer, nullable=False, default=60)

    # Exam settings
    is_active = Column(Boolean, default=True)
    allow_retakes = Column(Boolean, default=False)
    max_retakes = Column(Integer, default=0)  # 0 = unlimited if allow_retakes
    shuffle_questions = Column(Boolean, default=True)
    shuffle_options = Column(Boolean, default=True)
    show_result_immediately = Column(Boolean, default=False)  # False = needs verification

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    course = relationship("Course")
    module = relationship("CourseModule")
    institution = relationship("Institution")
    creator = relationship("User", foreign_keys=[created_by])
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.order_index")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")
    schedules = relationship("ExamSchedule", back_populates="exam", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exam {self.title}>"


class Question(Base):
    """
    MCQ questions for an exam. No institution_id of its own — always reached
    through the parent Exam. API invariant (F-14): student-facing schemas
    never serialize correct_option/explanation before the attempt is
    completed and verified.
    """
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Question content
    question_text = Column(Text, nullable=False)
    image_url = Column(Text)  # optional question image (Supabase Storage URL)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String(1), nullable=False)  # 'A', 'B', 'C', 'D'

    # Scoring
    marks = Column(Integer, default=1)
    order_index = Column(Integer, nullable=False, default=0)

    # Optional explanation (shown after verification only)
    explanation = Column(Text)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    exam = relationship("Exam", back_populates="questions")
    student_answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.id}>"


class ExamSchedule(Base):
    """
    Schedule an exam for exactly one batch (F-08). Scheduling one exam for
    three batches = three rows.
    """
    __tablename__ = "exam_schedules"
    __table_args__ = (
        UniqueConstraint("exam_id", "batch_id", "scheduled_date", name="uq_exam_schedules_exam_batch_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)

    # Schedule timing
    scheduled_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    exam = relationship("Exam", back_populates="schedules")
    institution = relationship("Institution")
    batch = relationship("Batch", back_populates="exam_schedules")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ExamSchedule {self.exam_id} on {self.scheduled_date}>"


class ExamAttempt(Base):
    """
    Student's exam attempt. State machine is driven by `status`
    (docs/03 §3): in_progress -> submitted | timed_out -> verified.
    `deadline_at` is the server-authoritative end of the attempt (F-13),
    computed at start as now() + duration; answers/submits are rejected past
    deadline_at + 30s grace. No institution_id of its own — reached through
    the parent Exam.
    """
    __tablename__ = "exam_attempts"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "attempt_number", name="uq_exam_attempts_exam_student_attempt"),
        CheckConstraint(
            "status IN ('in_progress','submitted','timed_out','verified')",
            name="ck_exam_attempts_status",
        ),
        Index("ix_exam_attempts_student_status", "student_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("exam_schedules.id", ondelete="SET NULL"), nullable=True)

    # Attempt tracking
    attempt_number = Column(Integer, default=1)
    start_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # F-13: server-authoritative deadline = start + duration, set at creation.
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))  # when submitted/timed out
    time_remaining_seconds = Column(Integer)  # display hint ONLY — never trusted

    # Status: in_progress | submitted | timed_out | verified
    status = Column(String, default="in_progress", index=True)

    # Results (populated after completion)
    total_marks = Column(Integer)
    obtained_marks = Column(Integer)
    percentage = Column(Float)
    passed = Column(Boolean)
    total_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    # Randomization storage
    question_order = Column(JSON)  # question IDs in randomized order
    answer_order = Column(JSON)  # question_id -> shuffled option mapping

    # Verification (audit columns; the state machine is driven by `status`)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at = Column(DateTime(timezone=True))
    verification_notes = Column(Text)

    # Retake info
    retake_allowed = Column(Boolean, default=False)
    retake_allowed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    retake_allowed_at = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    exam = relationship("Exam", back_populates="attempts")
    student = relationship("Student")
    schedule = relationship("ExamSchedule")
    verifier = relationship("User", foreign_keys=[verified_by])
    retake_approver = relationship("User", foreign_keys=[retake_allowed_by])
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExamAttempt {self.id} student={self.student_id} status={self.status}>"


class StudentAnswer(Base):
    """
    Individual answer for each question in an attempt. No institution_id of
    its own — reached through the parent ExamAttempt.
    """
    __tablename__ = "student_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_student_answers_attempt_question"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Answer details
    selected_option = Column(String(1))  # 'A'..'D' or NULL if not answered
    is_correct = Column(Boolean)  # NULL until graded
    marks_obtained = Column(Integer, default=0)

    # "Mark for review" feature
    marked_for_review = Column(Boolean, default=False)

    # Timestamps
    answered_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")

    def __repr__(self):
        return f"<StudentAnswer attempt={self.attempt_id} question={self.question_id}>"
