from pydantic import BaseModel
from typing import Optional
from datetime import datetime,date
from uuid import UUID


class PayrollGenerate(BaseModel):
    month: int  # 1-12
    year: int
    institution_id: Optional[UUID] = None  # Generate for all staff in institution


class PayrollResponse(BaseModel):
    id: UUID
    staff_id: UUID
    month: int
    year: int
    days_present: int
    days_half: int
    total_amount: float
    payslip_url: Optional[str] = None
    generated_at: datetime

    class Config:
        from_attributes = True


class CertificateGenerate(BaseModel):
    student_id: UUID
    course_id: UUID


class CertificateResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_id: UUID
    certificate_url: str
    issue_date: date
    certificate_number: str
    created_at: datetime

    class Config:
        from_attributes = True
