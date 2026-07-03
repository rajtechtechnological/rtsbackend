from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


class StudentBase(BaseModel):
    date_of_birth: Optional[date] = None
    father_name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    address: Optional[str] = None
    apaar_id: Optional[str] = None
    last_qualification: Optional[str] = None


class StudentCreate(StudentBase):
    """Create a student profile for an existing user.

    NOTE: no institution_id — it is always set server-side from the
    TenantContext (docs/01 §4).
    """
    user_id: UUID
    batch_id: UUID
    aadhar_number: Optional[str] = None


class StudentRegister(StudentBase):
    """Combined user + student registration (staff-driven, docs/01 §5)."""
    # User fields
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    # Student fields
    batch_id: UUID
    aadhar_number: Optional[str] = None
    # Course enrollment (optional)
    course_id: Optional[UUID] = None


class StudentUpdate(StudentBase):
    student_id: Optional[str] = None  # manual correction, uniqueness enforced
    batch_id: Optional[UUID] = None
    status: Optional[str] = None  # active | completed | dropped
    aadhar_number: Optional[str] = None


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


class StudentListItem(StudentBase):
    """List shape — deliberately excludes aadhar_number (sensitive, docs/02)."""
    id: UUID
    user_id: Optional[UUID] = None
    institution_id: UUID
    batch_id: UUID
    student_id: str
    status: str
    photo_url: Optional[str] = None
    enrollment_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserInfo] = None
    course_enrollments: Optional[List[StudentCourseInfo]] = []

    class Config:
        from_attributes = True


class StudentResponse(StudentListItem):
    """Single-student detail shape — includes aadhar_number (receptionist+)."""
    aadhar_number: Optional[str] = None


class CourseEnrollmentCreate(BaseModel):
    course_id: UUID


class FeePaymentCreate(BaseModel):
    """No institution_id — derived from the student via TenantContext."""
    student_id: UUID
    course_id: UUID
    amount: float
    paid_at: Optional[date] = None
    payment_method: str  # cash, online, upi, card, bank_transfer, offline
    transaction_id: Optional[str] = None  # required for online/upi/card
    notes: Optional[str] = None


class FeePaymentResponse(BaseModel):
    id: UUID
    institution_id: UUID
    student_id: UUID
    course_id: UUID
    amount: float
    paid_at: date
    payment_method: str
    transaction_id: Optional[str] = None
    receipt_number: str
    notes: Optional[str] = None
    recorded_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
