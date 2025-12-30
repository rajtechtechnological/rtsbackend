from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    duration_months = Column(Integer)
    fee_amount = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    institution = relationship("Institution", back_populates="courses")
    student_enrollments = relationship("StudentCourse", back_populates="course", cascade="all, delete-orphan")
    payments = relationship("FeePayment", back_populates="course")
    certificates = relationship("Certificate", back_populates="course")
    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan", order_by="CourseModule.order_index")
