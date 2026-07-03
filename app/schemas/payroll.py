from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class PayrollGenerate(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    # Honored ONLY for super_admin; tenant users always get their own
    # institution from TenantContext.
    institution_id: Optional[UUID] = None


class PayrollResponse(BaseModel):
    id: UUID
    institution_id: UUID
    staff_id: UUID
    month: int
    year: int
    days_present: int
    days_half: int
    total_amount: Optional[float] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class CertificateGenerate(BaseModel):
    student_id: UUID
    course_id: UUID


class CertificateResponse(BaseModel):
    id: UUID
    institution_id: UUID
    student_id: UUID
    course_id: UUID
    certificate_number: str
    verification_code: str
    issue_date: date
    created_at: datetime

    class Config:
        from_attributes = True
