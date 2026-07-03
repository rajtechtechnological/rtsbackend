"""
Atomic human-readable ID generation (F-05, docs/02-DATA-MODEL.md §6).

One counter table (`id_counters`), one helper, used for student IDs, receipt
numbers and certificate numbers. The counter bump is a single atomic
INSERT ... ON CONFLICT DO UPDATE ... RETURNING statement — race-free under
any concurrency. Counters only go up, so deleting a row never causes the
next number to collide.

Formats:
- Student:     RTS-{district_code}-{inst.code}-{MM}-{YYYY}-{NNNN}   (period 'MM-YYYY')
- Receipt:     RCP-{inst.code}-{YYYY}-{NNNNN}                        (period 'YYYY')
- Certificate: RTS-{district_code}-{inst.code}-CERT-{YYYY}-{NNNN}    (period 'YYYY')
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

KIND_STUDENT = "student"
KIND_RECEIPT = "receipt"
KIND_CERTIFICATE = "certificate"


def next_id(db: Session, institution_id: UUID, kind: str, period: str) -> int:
    """Atomically bump and return the counter for (institution, kind, period)."""
    return db.execute(
        text(
            """
            INSERT INTO id_counters (institution_id, kind, period, value)
            VALUES (:i, :k, :p, 1)
            ON CONFLICT (institution_id, kind, period)
            DO UPDATE SET value = id_counters.value + 1
            RETURNING value
            """
        ),
        {"i": str(institution_id), "k": kind, "p": period},
    ).scalar_one()


def student_id(db: Session, institution, month: int, year: int) -> str:
    """RTS-{DIST}-{INST}-{MM}-{YYYY}-{NNNN}"""
    period = f"{month:02d}-{year}"
    seq = next_id(db, institution.id, KIND_STUDENT, period)
    return f"RTS-{institution.district_code}-{institution.code}-{month:02d}-{year}-{seq:04d}"


def receipt_number(db: Session, institution, year: int) -> str:
    """RCP-{INST}-{YYYY}-{NNNNN}"""
    seq = next_id(db, institution.id, KIND_RECEIPT, str(year))
    return f"RCP-{institution.code}-{year}-{seq:05d}"


def certificate_number(db: Session, institution, year: int) -> str:
    """RTS-{DIST}-{INST}-CERT-{YYYY}-{NNNN}"""
    seq = next_id(db, institution.id, KIND_CERTIFICATE, str(year))
    return f"RTS-{institution.district_code}-{institution.code}-CERT-{year}-{seq:04d}"
