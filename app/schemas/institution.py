from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class InstitutionBase(BaseModel):
    name: str
    district_code: Optional[str] = None  # e.g., NAL, PAT, GAY
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class InstitutionCreate(InstitutionBase):
    director_id: Optional[UUID] = None


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    district_code: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    director_id: Optional[UUID] = None


class InstitutionResponse(InstitutionBase):
    id: UUID
    director_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
