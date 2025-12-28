from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class StaffBase(BaseModel):
    position: Optional[str] = None
    daily_rate: Optional[float] = None


class StaffCreate(BaseModel):
    """Schema for creating a new staff member (creates both User and Staff records)"""
    full_name: str
    email: EmailStr
    phone: str  # Required - used as default password
    role: str  # 'staff' or 'staff_manager'
    daily_rate: float
    institution_id: UUID


class StaffUpdate(StaffBase):
    pass


class StaffResponse(StaffBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    join_date: date  # Consistent naming with frontend
    created_at: datetime
    updated_at: Optional[datetime] = None

    # User information (from relationship)
    full_name: str
    email: str
    phone: str  # Required
    role: str
    status: str  # user.is_active -> 'active' or 'inactive'

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    staff_id: UUID
    date: date
    status: str  # present, absent, half_day, leave
    notes: Optional[str] = None


class AttendanceBatchCreate(BaseModel):
    date: date
    attendance: list[dict]  # [{staff_id: UUID, status: str}, ...]


class AttendanceResponse(BaseModel):
    id: UUID
    staff_id: UUID
    date: date
    status: str
    marked_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
