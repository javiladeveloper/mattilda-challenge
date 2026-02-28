from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class GradeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Grade name (e.g., '5th Grade')")
    monthly_fee: Decimal = Field(..., gt=0, description="Monthly tuition fee for this grade")


class GradeCreate(GradeBase):
    school_id: UUID = Field(..., description="School this grade belongs to")


class GradeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    monthly_fee: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None


class GradeResponse(GradeBase):
    id: UUID
    school_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GradeListResponse(BaseModel):
    items: List[GradeResponse]
    total: int
    page: int
    page_size: int
    pages: int
