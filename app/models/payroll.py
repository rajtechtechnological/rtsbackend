from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint('staff_id', 'month', 'year', name='unique_staff_month_year'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    days_present = Column(Integer, default=0)
    days_half = Column(Integer, default=0)
    total_amount = Column(Numeric(10, 2))
    payslip_url = Column(String)  # Cloudinary URL or local path
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="payroll_records")
