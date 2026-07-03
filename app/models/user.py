from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

# Canonical 6-role enum (docs/01-SYSTEM-DESIGN.md §3, F-06)
ROLES = (
    "super_admin",
    "institution_director",
    "staff_manager",
    "receptionist",
    "staff",
    "student",
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # F-06: exactly six canonical role strings
        CheckConstraint(
            "role IN ('super_admin','institution_director','staff_manager',"
            "'receptionist','staff','student')",
            name="ck_users_role",
        ),
        # institution_id is NULL if and only if role='super_admin'
        CheckConstraint(
            "(role = 'super_admin') = (institution_id IS NULL)",
            name="ck_users_super_admin_institution",
        ),
        # F-07: exactly one director per institution (partial unique index)
        Index(
            "one_director_per_institution",
            "institution_id",
            unique=True,
            postgresql_where=text("role = 'institution_director'"),
            sqlite_where=text("role = 'institution_director'"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)  # globally unique (F-10)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String)
    role = Column(String, nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    institution = relationship("Institution", foreign_keys=[institution_id], back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
