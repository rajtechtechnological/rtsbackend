from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class IdCounter(Base):
    """
    Atomic per-scope counters for human-readable IDs (F-05,
    docs/02-DATA-MODEL.md §6). Rows are only ever touched through
    app.ids.next_id() — a single INSERT ... ON CONFLICT DO UPDATE ...
    RETURNING statement, race-free under any concurrency. Counters only go
    up; deletion never reuses a number.
    """
    __tablename__ = "id_counters"

    institution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    kind = Column(String, primary_key=True)  # 'student' | 'receipt' | 'certificate'
    period = Column(String, primary_key=True)  # 'MM-YYYY' for students, 'YYYY' for others
    value = Column(Integer, nullable=False, server_default="0")
