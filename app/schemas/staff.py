from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class StaffBase(BaseModel):
    position: Optional[str] = None
    daily_rate: Optional[float] = None


class StaffCreate(StaffBase):
    user_id: UUID
    institution_id: UUID


class StaffUpdate(StaffBase):
    pass


class StaffResponse(StaffBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    joining_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None

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
