from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4

from src.domain.enums import InvoiceStatus, PaymentMethod
from src.domain.events import (
    DomainEvent,
    PaymentRecorded,
    InvoicePaid,
    InvoiceCancelled,
    InvoiceOverdue,
)
from src.domain.exceptions import BusinessRuleError, InvoiceCancelledError, PaymentExceedsDebtError
from src.domain.value_objects import Money


class Invoice:
    """Aggregate Root for invoices and payments."""

    def __init__(
        self,
        student_id: UUID,
        amount: Decimal | float | int,
        due_date: date,
        description: str = "",
        id: UUID | None = None,
        status: InvoiceStatus = InvoiceStatus.PENDING,
        payments: List[Payment] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        money = Money(amount)
        if money.is_zero():
            raise BusinessRuleError("Invoice amount must be greater than zero")

        self.id = id or uuid4()
        self.student_id = student_id
        self.amount = money.to_decimal()
        self.due_date = due_date
        self.description = description
        self.status = status
        self._payments: List[Payment] = list(payments or [])
        self._events: List[DomainEvent] = []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    @property
    def paid_amount(self) -> Decimal:
        return sum((p.amount for p in self._payments), Decimal("0"))

    @property
    def pending_amount(self) -> Decimal:
        return max(self.amount - self.paid_amount, Decimal("0"))

    @property
    def payments(self) -> List[Payment]:
        return list(self._payments)

    @property
    def domain_events(self) -> List[DomainEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def record_payment(
        self,
        amount: Decimal | float | int,
        method: PaymentMethod,
        reference: str = "",
        payment_date: date | None = None,
    ) -> Payment:
        if self.status == InvoiceStatus.CANCELLED:
            raise InvoiceCancelledError(self.id)

        money = Money(amount)
        pending_money = Money(self.pending_amount)

        if money > pending_money:
            raise PaymentExceedsDebtError(
                float(money.to_decimal()),
                float(pending_money.to_decimal()),
            )

        payment = Payment(
            invoice_id=self.id,
            amount=money.to_decimal(),
            method=method,
            reference=reference,
            payment_date=payment_date or date.today(),
        )
        self._payments.append(payment)
        self._update_status()
        self.updated_at = datetime.utcnow()

        self._events.append(PaymentRecorded(
            invoice_id=self.id,
            payment_id=payment.id,
            amount=money.to_decimal(),
            new_status=self.status.value,
        ))

        if self.status == InvoiceStatus.PAID:
            self._events.append(InvoicePaid(
                invoice_id=self.id,
                student_id=self.student_id,
                amount=self.amount,
            ))

        return payment

    def update_details(
        self,
        amount: Decimal | float | int | None = None,
        due_date: date | None = None,
        description: str | None = None,
    ) -> None:
        if self.status == InvoiceStatus.CANCELLED:
            raise BusinessRuleError("Cannot update a cancelled invoice")

        if amount is not None:
            new_amount = Money(amount).to_decimal()
            if new_amount < self.paid_amount:
                raise BusinessRuleError(
                    f"Cannot reduce amount below paid amount ({self.paid_amount})"
                )
            self.amount = new_amount

        if due_date is not None:
            self.due_date = due_date

        if description is not None:
            self.description = description

        self._update_status()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        if self.status == InvoiceStatus.CANCELLED:
            raise BusinessRuleError("Invoice is already cancelled")
        if self.paid_amount > Decimal("0"):
            raise BusinessRuleError("Cannot cancel an invoice with payments")
        self.status = InvoiceStatus.CANCELLED
        self.updated_at = datetime.utcnow()

        self._events.append(InvoiceCancelled(
            invoice_id=self.id,
            student_id=self.student_id,
        ))

    def mark_overdue(self) -> None:
        if self.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            return
        if self.due_date < date.today() and self.pending_amount > Decimal("0"):
            self.status = InvoiceStatus.OVERDUE
            self.updated_at = datetime.utcnow()

            self._events.append(InvoiceOverdue(
                invoice_id=self.id,
                student_id=self.student_id,
                days_overdue=(date.today() - self.due_date).days,
            ))

    def _update_status(self) -> None:
        if self.pending_amount == Decimal("0"):
            self.status = InvoiceStatus.PAID
        elif self.due_date < date.today():
            self.status = InvoiceStatus.OVERDUE
        elif self.paid_amount > Decimal("0"):
            self.status = InvoiceStatus.PARTIAL
        else:
            self.status = InvoiceStatus.PENDING


class Payment:
    """Child entity of Invoice aggregate."""

    def __init__(
        self,
        invoice_id: UUID,
        amount: Decimal | float | int,
        method: PaymentMethod,
        reference: str = "",
        payment_date: date | None = None,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        money = Money(amount)
        if money.is_zero():
            raise BusinessRuleError("Payment amount must be greater than zero")

        self.id = id or uuid4()
        self.invoice_id = invoice_id
        self.amount = money.to_decimal()
        self.method = method
        self.reference = reference
        self.payment_date = payment_date or date.today()
        self.created_at = created_at or datetime.utcnow()
