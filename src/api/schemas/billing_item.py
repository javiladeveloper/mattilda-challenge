from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class BillingItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Item name (e.g., 'Enrollment 2024')")
    description: Optional[str] = Field(None, description="Detailed description of the item")
    amount: Decimal = Field(..., gt=0, description="Amount for this item")
    is_recurring: bool = Field(default=False, description="Whether this is a recurring monthly charge")
    academic_year: Optional[str] = Field(None, max_length=20, description="Academic year (e.g., '2024')")


class BillingItemCreate(BillingItemBase):
    school_id: UUID = Field(..., description="School this item belongs to")


class BillingItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    is_recurring: Optional[bool] = None
    academic_year: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class BillingItemResponse(BillingItemBase):
    id: UUID
    school_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillingItemListResponse(BaseModel):
    items: List[BillingItemResponse]
    total: int
    page: int
    page_size: int
    pages: int
