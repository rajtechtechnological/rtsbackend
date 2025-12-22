from sqlalchemy import Column, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"
    __table_args__ = (
        UniqueConstraint('staff_id', 'date', name='unique_staff_date'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String, nullable=False)  # present, absent, half_day, leave
    marked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="attendance_records")
    marker = relationship("User", foreign_keys=[marked_by])
