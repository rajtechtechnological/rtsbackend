from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class InstitutionBase(BaseModel):
    name: str = Field(..., min_length=1)
    district_code: str = Field(..., min_length=2, max_length=8)  # e.g. NAL, PAT
    code: str = Field(..., min_length=2, max_length=8)  # short code for IDs, e.g. RCC
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    # UPI ID (e.g. rajtech@ybl) used for the fee-collection QR
    upi_vpa: Optional[str] = Field(None, pattern=r"^[\w.\-]{2,64}@[a-zA-Z]{2,32}$")


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    # district_code / code are intentionally NOT updatable: they are baked
    # into issued student/receipt/certificate IDs.
    name: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    upi_vpa: Optional[str] = Field(None, pattern=r"^[\w.\-]{2,64}@[a-zA-Z]{2,32}$")


class InstitutionStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]


class InstitutionResponse(InstitutionBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
