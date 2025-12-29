from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class FeePayment(Base):
    __tablename__ = "fee_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, server_default=func.current_date())
    payment_method = Column(String, nullable=False)  # online, offline, cash, upi, card, bank_transfer
    transaction_id = Column(String)  # For online/UPI/card payments
    receipt_number = Column(String, unique=True, index=True)  # Auto-generated: RCT-INST-YYYY-001
    receipt_url = Column(String)  # PDF receipt URL
    notes = Column(String)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Who recorded the payment
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="payments")
    course = relationship("Course", back_populates="payments")
    created_by_user = relationship("User", foreign_keys=[created_by])
