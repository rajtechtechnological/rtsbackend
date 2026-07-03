from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class FeePayment(Base):
    __tablename__ = "fee_payments"
    __table_args__ = (
        Index("ix_fee_payments_institution_paid_at", "institution_id", "paid_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Denormalized (docs/02): payments are directly RLS-protected and revenue
    # queries don't join through students.
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_at = Column(Date, server_default=func.current_date())
    payment_method = Column(String, nullable=False)  # cash, online, upi, card, bank_transfer, offline
    transaction_id = Column(String)  # for online/UPI/card payments
    # Unique, generated via id_counters (§6): RCP-{INST}-{YYYY}-{NNNNN}
    receipt_number = Column(String, unique=True, nullable=False, index=True)
    notes = Column(String)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="payments")
    course = relationship("Course", back_populates="payments")
    recorded_by_user = relationship("User", foreign_keys=[recorded_by])
