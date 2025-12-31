from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class StudentBase(BaseModel):
    date_of_birth: Optional[date] = None
    father_name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    address: Optional[str] = None
    aadhar_number: Optional[str] = None
    apaar_id: Optional[str] = None  # APAAR ID (Automated Permanent Academic Account Registry)
    last_qualification: Optional[str] = None
    # Batch Information
    batch_time: Optional[str] = None  # e.g., "9AM-10AM", "10AM-11AM"
    batch_month: Optional[str] = None  # MM format
    batch_year: Optional[str] = None  # YYYY format
    batch_identifier: Optional[str] = None  # "A" or "B"


class StudentCreate(StudentBase):
    user_id: UUID
    institution_id: UUID


class StudentUpdate(StudentBase):
    student_id: Optional[str] = None  # Allow manual editing of student ID


class UserInfo(BaseModel):
    """Nested user info for student response"""
    full_name: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class StudentCourseInfo(BaseModel):
    """Course enrollment info for student response"""
    id: UUID
    course_id: UUID
    enrollment_date: date
    status: Optional[str] = None

    class Config:
        from_attributes = True


class StudentResponse(StudentBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    student_id: Optional[str] = None  # Format: RTS-DISTRICT-INST-MM-YYYY-NNNN
    father_name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    address: Optional[str] = None
    aadhar_number: Optional[str] = None
    apaar_id: Optional[str] = None
    last_qualification: Optional[str] = None
    batch_time: Optional[str] = None
    batch_month: Optional[str] = None
    batch_year: Optional[str] = None
    batch_identifier: Optional[str] = None
    photo_url: Optional[str] = None
    enrollment_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserInfo] = None  # Nested user object
    course_enrollments: Optional[list[StudentCourseInfo]] = []  # Course enrollments

    class Config:
        from_attributes = True


class StudentRegister(BaseModel):
    """Combined user + student registration"""
    # User fields
    full_name: str
    email: str
    phone: Optional[str] = None
    # Student fields
    date_of_birth: Optional[date] = None
    father_name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    address: Optional[str] = None
    aadhar_number: Optional[str] = None
    apaar_id: Optional[str] = None
    last_qualification: Optional[str] = None
    # Batch fields
    batch_time: Optional[str] = None
    batch_month: Optional[str] = None
    batch_year: Optional[str] = None
    batch_identifier: Optional[str] = None
    # Course enrollment (optional)
    course_id: Optional[UUID] = None


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
