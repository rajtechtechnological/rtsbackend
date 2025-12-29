from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class StudentBase(BaseModel):
    date_of_birth: Optional[date] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    address: Optional[str] = None


class StudentCreate(StudentBase):
    user_id: UUID
    institution_id: UUID


class StudentUpdate(StudentBase):
    student_id: Optional[str] = None  # Allow manual editing of student ID


class StudentResponse(StudentBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    student_id: Optional[str] = None  # Format: RTS-DISTRICT-INST-MM-YYYY-NNNN
    photo_url: Optional[str] = None
    enrollment_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseEnrollmentCreate(BaseModel):
    course_id: UUID


class FeePaymentCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    amount: float
    payment_date: Optional[date] = None
    payment_method: str  # Required: online, offline, cash, upi, card, bank_transfer
    transaction_id: Optional[str] = None  # Required for online/upi/card
    notes: Optional[str] = None


class FeePaymentResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_id: UUID
    amount: float
    payment_date: date
    payment_method: str
    transaction_id: Optional[str] = None
    receipt_number: str
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True
