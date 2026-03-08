from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class PaymentRecorded(DomainEvent):
    invoice_id: UUID = field(default_factory=UUID)
    payment_id: UUID = field(default_factory=UUID)
    amount: Decimal = Decimal("0")
    new_status: str = ""


@dataclass(frozen=True)
class InvoicePaid(DomainEvent):
    invoice_id: UUID = field(default_factory=UUID)
    student_id: UUID = field(default_factory=UUID)
    amount: Decimal = Decimal("0")


@dataclass(frozen=True)
class InvoiceCancelled(DomainEvent):
    invoice_id: UUID = field(default_factory=UUID)
    student_id: UUID = field(default_factory=UUID)


@dataclass(frozen=True)
class InvoiceOverdue(DomainEvent):
    invoice_id: UUID = field(default_factory=UUID)
    student_id: UUID = field(default_factory=UUID)
    days_overdue: int = 0


@dataclass(frozen=True)
class StudentDeactivated(DomainEvent):
    student_id: UUID = field(default_factory=UUID)
    school_id: UUID = field(default_factory=UUID)


@dataclass(frozen=True)
class SchoolDeactivated(DomainEvent):
    school_id: UUID = field(default_factory=UUID)
