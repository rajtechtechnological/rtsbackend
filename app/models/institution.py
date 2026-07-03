from sqlalchemy import Column, String, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Institution(Base):
    """
    Franchise institution (tenant root).

    Per docs/02-DATA-MODEL.md:
    - director_id removed (F-07): the director is the users row with
      role='institution_director' and matching institution_id, enforced by
      the partial unique index one_director_per_institution (on users).
    - code: short institution code used in human-readable IDs (e.g. RCC),
      set once at creation — never re-derived from name.
    - status: super_admin can suspend a franchise; login refused while
      suspended.
    """
    __tablename__ = "institutions"
    __table_args__ = (
        UniqueConstraint("district_code", "code", name="uq_institutions_district_code_code"),
        CheckConstraint("status IN ('active','suspended')", name="ck_institutions_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    district_code = Column(String, nullable=False)  # e.g. NAL, PAT (used in student IDs)
    code = Column(String, nullable=False)  # short institution code for IDs, e.g. RCC
    status = Column(String, nullable=False, server_default="active")  # active | suspended
    address = Column(String)
    contact_email = Column(String)
    contact_phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", foreign_keys="User.institution_id", back_populates="institution")
    students = relationship("Student", back_populates="institution", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="institution", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="institution", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="institution", cascade="all, delete-orphan")
