"""
Tenant isolation layer (docs/01-SYSTEM-DESIGN.md §4, fixes F-01/F-02/F-03).

Layer 1 (application): `TenantContext` — every tenant-scoped endpoint uses
`ctx.q(Model)` instead of raw `db.query(Model)`. Layer 2 (defense in depth):
`get_tenant` arms Postgres RLS for the transaction via
set_config('app.institution_id', ...), so a forgotten filter returns 0 rows
instead of another tenant's data.

Rules:
- Tables without their own institution_id (questions, student_answers,
  student_courses, course_modules, student_module_progress) are reached ONLY
  through their parent (exam, attempt, student, course), fetched via ctx.q.
- Writes: institution_id is always set server-side from ctx.institution_id —
  never accepted from the request body (super_admin-only endpoints may pass
  one explicitly, see require_institution_id).
- Rows outside the tenant scope are indistinguishable from missing rows:
  endpoints return 404, not 403.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User


@dataclass
class TenantContext:
    db: Session
    user: User
    institution_id: Optional[UUID]  # None only for super_admin

    def q(self, model):
        """Tenant-scoped query. The ONLY sanctioned way to query tenant tables."""
        query = self.db.query(model)
        if self.institution_id is not None:  # not super_admin
            query = query.filter(model.institution_id == self.institution_id)
        return query

    def require_institution_id(self, requested: Optional[UUID] = None) -> UUID:
        """institution_id for a write. Tenant users always get their own
        institution (request input is ignored); super_admin must state one
        explicitly (F-04)."""
        if self.institution_id is not None:
            return self.institution_id
        if requested is None:
            raise HTTPException(
                status_code=400,
                detail="institution_id is required for super_admin",
            )
        return requested


def get_tenant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    inst = None if user.role == "super_admin" else user.institution_id
    if inst is None and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="User has no institution")
    # Arms RLS for this transaction ('' = super_admin sees all)
    db.execute(
        text("SELECT set_config('app.institution_id', :v, true)"),
        {"v": str(inst or "")},
    )
    return TenantContext(db=db, user=user, institution_id=inst)
