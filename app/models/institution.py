from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    district_code = Column(String)  # e.g., NAL for Nalanda, PAT for Patna
    address = Column(String)
    contact_email = Column(String)
    contact_phone = Column(String)
    director_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    director = relationship("User", foreign_keys=[director_id])
    users = relationship("User", foreign_keys="User.institution_id", back_populates="institution")
    students = relationship("Student", back_populates="institution", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="institution", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="institution", cascade="all, delete-orphan")
