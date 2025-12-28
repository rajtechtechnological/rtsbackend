from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_months: Optional[int] = None
    fee_amount: Optional[float] = None


class CourseCreate(CourseBase):
    institution_id: Optional[UUID] = None


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_months: Optional[int] = None
    fee_amount: Optional[float] = None


class CourseResponse(CourseBase):
    id: UUID
    institution_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
