from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SchoolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None


class SchoolCreate(SchoolBase):
    pass


class SchoolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class SchoolResponse(SchoolBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchoolListResponse(BaseModel):
    items: List[SchoolResponse]
    total: int
    page: int
    page_size: int
    pages: int
