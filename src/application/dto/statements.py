from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from src.domain.enums import InvoiceStatus, PaymentMethod


@dataclass
class PaymentSummaryDTO:
    amount: Decimal
    date: date
    method: PaymentMethod


@dataclass
class InvoiceSummaryDTO:
    id: UUID
    description: Optional[str]
    amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    status: InvoiceStatus
    due_date: date
    student_name: Optional[str] = None
    payments: Optional[List[PaymentSummaryDTO]] = None


@dataclass
class FinancialSummaryDTO:
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    total_overdue: Decimal


@dataclass
class PeriodDTO:
    from_date: Optional[date]
    to_date: Optional[date]


@dataclass
class SchoolStatementDTO:
    school_id: UUID
    school_name: str
    period: PeriodDTO
    summary: FinancialSummaryDTO
    total_students: int
    active_students: int
    invoices: List[InvoiceSummaryDTO]
    generated_at: datetime


@dataclass
class StudentStatementDTO:
    student_id: UUID
    student_name: str
    school_name: str
    summary: FinancialSummaryDTO
    invoices: List[InvoiceSummaryDTO]
    generated_at: datetime
