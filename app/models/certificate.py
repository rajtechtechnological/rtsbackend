from sqlalchemy import Column, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Certificate(Base):
    """
    Certificate record. No pdf_url — certificates are rendered on demand from
    data + template (docs/01 §2). verification_code backs the public
    QR-verify endpoint.
    """
    __tablename__ = "certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Denormalized (docs/02): same rationale as fee_payments.
    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    # Unique, generated via id_counters (§6): RTS-{DIST}-{INST}-CERT-{YYYY}-{NNNN}
    certificate_number = Column(String, unique=True, nullable=False)
    verification_code = Column(String, unique=True, nullable=False)  # random, for public QR verify
    issue_date = Column(Date, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="certificates")
    course = relationship("Course", back_populates="certificates")
