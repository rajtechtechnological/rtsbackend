from pydantic import BaseModel, EmailStr
from typing import Optional, Literal, List, Dict
from datetime import date, datetime
from uuid import UUID


class StaffBase(BaseModel):
    position: Optional[str] = None
    daily_rate: Optional[float] = None


class StaffCreate(BaseModel):
    """Creates both User and Staff records.

    NOTE: no institution_id — always set server-side from TenantContext
    (super_admin passes ?institution_id explicitly, see route).
    """
    full_name: str
    email: EmailStr
    phone: str  # required — used as default password
    role: Literal["staff", "staff_manager", "receptionist"]
    daily_rate: float


class StaffUpdate(StaffBase):
    pass


class StaffResponse(StaffBase):
    id: UUID
    user_id: UUID
    institution_id: UUID
    join_date: date  # consistent naming with frontend
    created_at: datetime
    updated_at: Optional[datetime] = None

    # User information (from relationship)
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str  # user.is_active -> 'active' or 'inactive'

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    staff_id: UUID
    date: date
    status: Literal["present", "absent", "half_day", "leave"]
    notes: Optional[str] = None


class AttendanceBatchCreate(BaseModel):
    date: date
    attendance: List[Dict[str, str]]  # [{staff_id: UUID, status: str}, ...]


class AttendanceResponse(BaseModel):
    id: UUID
    institution_id: UUID
    staff_id: UUID
    date: date
    status: str
    marked_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
