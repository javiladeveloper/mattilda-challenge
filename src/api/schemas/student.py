from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, computed_field


class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class StudentCreate(StudentBase):
    school_id: UUID
    grade_id: UUID = Field(..., description="Grade ID (required, determines monthly tuition)")


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    grade_id: Optional[UUID] = Field(None, description="Grade ID")
    school_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    id: UUID
    school_id: UUID
    grade_id: Optional[UUID] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    grade_name: Optional[str] = Field(None, description="Grade name from grades table")
    monthly_fee: Optional[Decimal] = Field(None, description="Monthly tuition fee from grade")
    enrolled_at: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_student(cls, student) -> "StudentResponse":
        """Create response from Student model with grade info."""
        grade_name = None
        monthly_fee = None
        if student.grade_ref:
            grade_name = student.grade_ref.name
            monthly_fee = student.grade_ref.monthly_fee
        elif student.grade:  # Legacy fallback
            grade_name = student.grade

        return cls(
            id=student.id,
            school_id=student.school_id,
            grade_id=student.grade_id,
            first_name=student.first_name,
            last_name=student.last_name,
            email=student.email,
            grade_name=grade_name,
            monthly_fee=monthly_fee,
            enrolled_at=student.enrolled_at,
            is_active=student.is_active,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )


class StudentListResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
    pages: int
