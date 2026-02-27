from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import InvoiceStatus


class InvoiceBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    due_date: date
    description: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    student_id: UUID


class InvoiceUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    due_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    student_id: UUID
    status: InvoiceStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceDetailResponse(InvoiceResponse):
    paid_amount: Decimal
    pending_amount: Decimal


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int
