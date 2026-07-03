from sqlalchemy import Column, String, Date, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','dropped')",
            name="ck_students_status",
        ),
        Index("ix_students_institution_batch", "institution_id", "batch_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # F-08: FK to first-class batches table (replaces the 4 free-text columns)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Human-readable ID via id_counters (§6): RTS-{DIST}-{INST}-{MM}-{YYYY}-{NNNN}
    student_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, nullable=False, server_default="active")  # active | completed | dropped
    date_of_birth = Column(Date)
    father_name = Column(String)
    guardian_name = Column(String)
    guardian_phone = Column(String)
    address = Column(String)
    # Sensitive: never serialized in list endpoints, only in the
    # single-student detail view for receptionist+ (docs/02 §2).
    aadhar_number = Column(String)
    apaar_id = Column(String)  # APAAR ID
    last_qualification = Column(String)
    photo_url = Column(String)
    enrollment_date = Column(Date, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    institution = relationship("Institution", back_populates="students")
    batch = relationship("Batch", back_populates="students")
    course_enrollments = relationship("StudentCourse", back_populates="student", cascade="all, delete-orphan")
    payments = relationship("FeePayment", back_populates="student", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="student", cascade="all, delete-orphan")
    module_progress = relationship("StudentModuleProgress", back_populates="student", cascade="all, delete-orphan")
