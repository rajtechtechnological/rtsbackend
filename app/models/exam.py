from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Time, ForeignKey, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Exam(Base):
    """
    Exam configuration for a course module
    """
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Exam details
    title = Column(String, nullable=False)
    description = Column(Text)
    total_questions = Column(Integer, nullable=False, default=0)
    passing_marks = Column(Integer, nullable=False, default=40)
    duration_minutes = Column(Integer, nullable=False, default=60)

    # Batch targeting - which batch this exam is for
    batch_time = Column(String, index=True)  # e.g., "9AM-10AM"
    batch_month = Column(String, index=True)  # MM format
    batch_year = Column(String, index=True)  # YYYY format
    batch_identifier = Column(String, index=True)  # "A" or "B"

    # Exam settings
    is_active = Column(Boolean, default=True)
    allow_retakes = Column(Boolean, default=False)
    max_retakes = Column(Integer, default=0)  # 0 = unlimited if allow_retakes is True
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
    MCQ questions for an exam
    """
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Question content
    question_text = Column(Text, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String(1), nullable=False)  # 'A', 'B', 'C', 'D'

    # Scoring
    marks = Column(Integer, default=1)
    order_index = Column(Integer, nullable=False, default=0)

    # Optional explanation
    explanation = Column(Text)  # Shown after exam completion

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
    Schedule exams for specific batches
    """
    __tablename__ = "exam_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Batch targeting
    batch_time = Column(String, nullable=False, index=True)  # e.g., "9AM-10AM"
    batch_identifier = Column(String, index=True)  # 'A' or 'B' (optional)
    batch_month = Column(String, index=True)  # MM format (optional filter)
    batch_year = Column(String, index=True)  # YYYY format (optional filter)

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
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ExamSchedule {self.exam_id} on {self.scheduled_date}>"


class ExamAttempt(Base):
    """
    Student's exam attempt tracking
    """
    __tablename__ = "exam_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("exam_schedules.id", ondelete="SET NULL"), nullable=True)

    # Attempt tracking
    attempt_number = Column(Integer, default=1)
    start_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_time = Column(DateTime(timezone=True))  # When submitted/timed out
    time_remaining_seconds = Column(Integer)  # For resume functionality

    # Status: in_progress, completed, timed_out, submitted
    status = Column(String, default='in_progress', index=True)

    # Results (populated after completion)
    total_marks = Column(Integer)
    obtained_marks = Column(Integer)
    percentage = Column(Float)
    passed = Column(Boolean)
    total_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    # Randomization storage
    question_order = Column(JSON)  # List of question IDs in randomized order
    answer_order = Column(JSON)  # Dict of question_id -> shuffled options mapping

    # Verification
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
    Individual answer for each question in an attempt
    """
    __tablename__ = "student_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Answer details
    selected_option = Column(String(1))  # 'A', 'B', 'C', 'D' or NULL if not answered
    is_correct = Column(Boolean)  # NULL until graded
    marks_obtained = Column(Integer, default=0)

    # For "mark for review" feature
    marked_for_review = Column(Boolean, default=False)

    # Timestamps
    answered_at = Column(DateTime(timezone=True))  # When first answered
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("Question", back_populates="student_answers")

    def __repr__(self):
        return f"<StudentAnswer attempt={self.attempt_id} question={self.question_id}>"
