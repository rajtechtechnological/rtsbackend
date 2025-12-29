from sqlalchemy import Column, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String, unique=True, index=True)  # Format: RTS-INST-MM-YYYY-NNNN
    date_of_birth = Column(Date)
    guardian_name = Column(String)
    guardian_phone = Column(String)
    address = Column(String)
    photo_url = Column(String)  # Cloudinary URL or local path
    enrollment_date = Column(Date, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    institution = relationship("Institution", back_populates="students")
    course_enrollments = relationship("StudentCourse", back_populates="student", cascade="all, delete-orphan")
    payments = relationship("FeePayment", back_populates="student", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="student", cascade="all, delete-orphan")
