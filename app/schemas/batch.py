from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time
from uuid import UUID


class BatchBase(BaseModel):
    name: str = Field(..., min_length=1)
    start_time: time
    end_time: time
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000, le=2100)
    identifier: str = "A"


class BatchCreate(BatchBase):
    # Honored ONLY for super_admin (tenant users always get their own
    # institution from TenantContext).
    institution_id: Optional[UUID] = None


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    identifier: Optional[str] = None
    is_active: Optional[bool] = None


class BatchResponse(BatchBase):
    id: UUID
    institution_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
