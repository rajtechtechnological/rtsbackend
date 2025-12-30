from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class CourseModule(Base):
    """
    Course modules - each course is divided into modules
    Future-ready for online test system
    """
    __tablename__ = "course_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)

    # Module identification
    module_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    module_name = Column(String, nullable=False)  # e.g., "Fundamentals & Windows-10"
    description = Column(Text)  # Syllabus topics

    # Module details
    lesson_count = Column(Integer, default=0)  # Number of lessons/topics
    duration_hours = Column(Integer)  # Estimated hours to complete

    # Exam configuration
    total_marks = Column(Float, default=100)
    passing_marks = Column(Float, default=40)

    # Display order
    order_index = Column(Integer, nullable=False)  # For sorting modules

    # Future online test fields
    has_online_test = Column(Boolean, default=False)  # Enable when online test system is ready
    test_duration_minutes = Column(Integer)  # For future online tests

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="modules")
    student_progress = relationship("StudentModuleProgress", back_populates="module", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CourseModule {self.module_number}: {self.module_name}>"


class StudentModuleProgress(Base):
    """
    Tracks student progress through course modules
    Supports both manual marking (current) and auto-grading (future)
    """
    __tablename__ = "student_module_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Student and course info
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("student_courses.id", ondelete="CASCADE"))

    # Progress status
    status = Column(String, default='not_started')  # not_started, in_progress, completed, failed

    # Exam results (manual marking - current system)
    marks_obtained = Column(Float)  # NULL until exam taken
    exam_date = Column(DateTime(timezone=True))  # When marks were entered
    passed = Column(Boolean)  # Auto-calculated based on passing_marks

    # Who entered the marks (for manual marking)
    marked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Accountant who entered marks
    notes = Column(Text)  # Optional feedback from accountant

    # Future online test fields
    test_attempt_id = Column(UUID(as_uuid=True))  # FK to test_attempts table (future)
    auto_graded = Column(Boolean, default=False)  # True if graded by system

    # Timestamps
    started_at = Column(DateTime(timezone=True))  # When student started module
    completed_at = Column(DateTime(timezone=True))  # When module was completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    student = relationship("Student", back_populates="module_progress")
    course = relationship("Course")
    module = relationship("CourseModule", back_populates="student_progress")
    marked_by_user = relationship("User", foreign_keys=[marked_by])

    def __repr__(self):
        return f"<StudentModuleProgress student={self.student_id} module={self.module_id} status={self.status}>"
