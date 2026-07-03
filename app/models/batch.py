from sqlalchemy import Column, String, Boolean, DateTime, Time, SmallInteger, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Batch(Base):
    """
    First-class batch entity (F-08) — replaces the 4 free-text batch columns
    previously duplicated across students / exams / exam_schedules.
    """
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "start_time", "month", "year", "identifier",
            name="uq_batches_institution_slot",
        ),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_batches_month"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)  # display, e.g. "Morning A — Jan 2026"
    start_time = Column(Time, nullable=False)  # replaces free-text batch_time
    end_time = Column(Time, nullable=False)
    month = Column(SmallInteger, nullable=False)  # 1–12
    year = Column(SmallInteger, nullable=False)
    identifier = Column(String, nullable=False, server_default="A")  # A/B split
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    institution = relationship("Institution", back_populates="batches")
    students = relationship("Student", back_populates="batch")
    exam_schedules = relationship("ExamSchedule", back_populates="batch")
