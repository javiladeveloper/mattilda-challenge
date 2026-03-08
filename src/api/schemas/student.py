from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class StudentCreate(StudentBase):
    school_id: UUID
    grade: Optional[str] = Field(None, max_length=50, description="Grade/level (e.g., '5th Grade')")


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    grade: Optional[str] = Field(None, max_length=50)
    school_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    id: UUID
    school_id: UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    grade: Optional[str] = None
    enrolled_at: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
    pages: int
