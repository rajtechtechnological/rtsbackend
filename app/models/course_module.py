from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class CourseModule(Base):
    """
    Course modules — each course is divided into modules. No institution_id
    of its own: always reached through the parent Course.
    """
    __tablename__ = "course_modules"
    __table_args__ = (
        UniqueConstraint("course_id", "module_number", name="uq_course_modules_course_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    # Module identification
    module_number = Column(Integer, nullable=False)  # 1, 2, 3, ...
    module_name = Column(String, nullable=False)
    description = Column(Text)  # syllabus topics

    # Module details
    lesson_count = Column(Integer, default=0)
    duration_hours = Column(Integer)

    # Exam configuration
    total_marks = Column(Float, default=100)
    passing_marks = Column(Float, default=40)

    # Display order
    order_index = Column(Integer, nullable=False)

    # Online test fields
    has_online_test = Column(Boolean, default=False)
    test_duration_minutes = Column(Integer)

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
    Tracks student progress through course modules. No institution_id of its
    own: always reached through the parent Student.
    """
    __tablename__ = "student_module_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "module_id", name="uq_student_module_progress_student_module"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("student_courses.id", ondelete="CASCADE"))

    # Progress status
    status = Column(String, default="not_started")  # not_started, in_progress, completed, failed

    # Exam results (manual marking)
    marks_obtained = Column(Float)
    exam_date = Column(DateTime(timezone=True))
    passed = Column(Boolean)

    marked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes = Column(Text)

    # Online test fields
    test_attempt_id = Column(UUID(as_uuid=True))
    auto_graded = Column(Boolean, default=False)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    student = relationship("Student", back_populates="module_progress")
    course = relationship("Course")
    module = relationship("CourseModule", back_populates="student_progress")
    marked_by_user = relationship("User", foreign_keys=[marked_by])

    def __repr__(self):
        return f"<StudentModuleProgress student={self.student_id} module={self.module_id} status={self.status}>"
