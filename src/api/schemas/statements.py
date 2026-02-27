from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from src.domain.enums import InvoiceStatus, PaymentMethod


class PaymentSummary(BaseModel):
    amount: Decimal
    date: date
    method: PaymentMethod


class InvoiceSummary(BaseModel):
    id: UUID
    description: Optional[str]
    amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    status: InvoiceStatus
    due_date: date
    student_name: Optional[str] = None
    payments: Optional[List[PaymentSummary]] = None


class FinancialSummary(BaseModel):
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    total_overdue: Decimal


class Period(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None

    class Config:
        populate_by_name = True


class SchoolStatementResponse(BaseModel):
    school_id: UUID
    school_name: str
    period: Period
    summary: FinancialSummary
    total_students: int
    active_students: int
    invoices: List[InvoiceSummary]
    generated_at: datetime


class StudentStatementResponse(BaseModel):
    student_id: UUID
    student_name: str
    school_name: str
    summary: FinancialSummary
    invoices: List[InvoiceSummary]
    generated_at: datetime
