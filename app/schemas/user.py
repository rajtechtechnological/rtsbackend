from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

# Canonical 6-role enum (docs/01 §3, F-06) — enforced here AND by the DB CHECK.
Role = Literal[
    "super_admin",
    "institution_director",
    "staff_manager",
    "receptionist",
    "staff",
    "student",
]


# Base schema with common fields
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: Role
    institution_id: Optional[UUID] = None


# Schema for creating a user (super_admin only — no public signup)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# Schema for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Schema for updating user profile
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


# Schema for response (without password)
class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Schema for token response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Schema for token data
class TokenData(BaseModel):
    user_id: Optional[UUID] = None
