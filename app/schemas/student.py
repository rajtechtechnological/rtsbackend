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
    pass


class StudentResponse(StudentBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    photo_url: Optional[str] = None
    enrollment_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseEnrollmentCreate(BaseModel):
    course_id: UUID


class FeePaymentCreate(BaseModel):
    course_id: UUID
    amount: float
    payment_method: Optional[str] = None
    notes: Optional[str] = None
