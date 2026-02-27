from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.enums import PaymentMethod


class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    reference: Optional[str] = Field(None, max_length=255)


class PaymentCreate(PaymentBase):
    invoice_id: UUID
    payment_date: Optional[date] = None


class PaymentResponse(PaymentBase):
    id: UUID
    invoice_id: UUID
    payment_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int
