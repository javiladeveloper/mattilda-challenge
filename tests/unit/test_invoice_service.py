"""Unit tests for Invoice business logic through domain entities.

These tests exercise the Invoice aggregate root and its invariants,
ensuring business rules are enforced by the domain model itself.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from src.domain.entities.invoice import Invoice, Payment
from src.domain.enums import InvoiceStatus, PaymentMethod
from src.domain.exceptions import (
    BusinessRuleError,
    PaymentExceedsDebtError,
    InvoiceCancelledError,
)


def _make_invoice(
    amount=500,
    due_date=None,
    status=InvoiceStatus.PENDING,
    payments=None,
):
    return Invoice(
        student_id=uuid4(),
        amount=amount,
        due_date=due_date or date.today() + timedelta(days=30),
        description="Test invoice",
        status=status,
        payments=payments,
    )


class TestInvoiceStatusCalculation:
    """Invoice status transitions driven by record_payment()."""

    def test_pending_when_no_payments(self):
        inv = _make_invoice()
        assert inv.status == InvoiceStatus.PENDING
        assert inv.paid_amount == Decimal("0")
        assert inv.pending_amount == Decimal("500")

    def test_partial_after_partial_payment(self):
        inv = _make_invoice(amount=500)
        inv.record_payment(200, PaymentMethod.CASH)

        assert inv.status == InvoiceStatus.PARTIAL
        assert inv.paid_amount == Decimal("200")
        assert inv.pending_amount == Decimal("300")

    def test_paid_after_full_payment(self):
        inv = _make_invoice(amount=500)
        inv.record_payment(500, PaymentMethod.BANK_TRANSFER)

        assert inv.status == InvoiceStatus.PAID
        assert inv.paid_amount == Decimal("500")
        assert inv.pending_amount == Decimal("0")

    def test_paid_after_multiple_payments(self):
        inv = _make_invoice(amount=500)
        inv.record_payment(200, PaymentMethod.CASH)
        inv.record_payment(300, PaymentMethod.CREDIT_CARD)

        assert inv.status == InvoiceStatus.PAID
        assert len(inv.payments) == 2

    def test_overdue_status_on_past_due_date(self):
        inv = _make_invoice(due_date=date.today() - timedelta(days=5))
        inv.mark_overdue()
        assert inv.status == InvoiceStatus.OVERDUE


class TestPaymentValidation:
    """Aggregate-enforced payment invariants."""

    def test_payment_cannot_exceed_pending(self):
        inv = _make_invoice(amount=300)
        with pytest.raises(PaymentExceedsDebtError):
            inv.record_payment(400, PaymentMethod.CASH)

    def test_payment_equal_to_pending_is_valid(self):
        inv = _make_invoice(amount=300)
        payment = inv.record_payment(300, PaymentMethod.CASH)
        assert payment.amount == Decimal("300")

    def test_cannot_pay_cancelled_invoice(self):
        inv = _make_invoice()
        inv.cancel()
        with pytest.raises(InvoiceCancelledError):
            inv.record_payment(100, PaymentMethod.CASH)

    def test_record_payment_returns_payment_entity(self):
        inv = _make_invoice(amount=500)
        payment = inv.record_payment(100, PaymentMethod.CASH, reference="REF-001")

        assert isinstance(payment, Payment)
        assert payment.invoice_id == inv.id
        assert payment.amount == Decimal("100")
        assert payment.method == PaymentMethod.CASH
        assert payment.reference == "REF-001"


class TestInvoiceCancellation:
    """Cancellation business rules."""

    def test_cancel_pending_invoice(self):
        inv = _make_invoice()
        inv.cancel()
        assert inv.status == InvoiceStatus.CANCELLED

    def test_cannot_cancel_with_payments(self):
        inv = _make_invoice(amount=500)
        inv.record_payment(100, PaymentMethod.CASH)
        with pytest.raises(BusinessRuleError, match="payments"):
            inv.cancel()

    def test_cannot_cancel_already_cancelled(self):
        inv = _make_invoice()
        inv.cancel()
        with pytest.raises(BusinessRuleError, match="already cancelled"):
            inv.cancel()


class TestInvoiceUpdateDetails:
    """update_details() invariant protection."""

    def test_update_amount(self):
        inv = _make_invoice(amount=500)
        inv.update_details(amount=700)
        assert inv.amount == Decimal("700")

    def test_cannot_reduce_below_paid(self):
        inv = _make_invoice(amount=500)
        inv.record_payment(300, PaymentMethod.CASH)
        with pytest.raises(BusinessRuleError, match="paid amount"):
            inv.update_details(amount=200)

    def test_cannot_update_cancelled(self):
        inv = _make_invoice()
        inv.cancel()
        with pytest.raises(BusinessRuleError, match="cancelled"):
            inv.update_details(description="new desc")

    def test_update_due_date(self):
        inv = _make_invoice()
        new_date = date.today() + timedelta(days=60)
        inv.update_details(due_date=new_date)
        assert inv.due_date == new_date


class TestFinancialCalculations:
    """Cross-invoice financial aggregations using domain entities."""

    def test_total_debt_across_invoices(self):
        invoices = [
            _make_invoice(amount=500),   # pending 500
            _make_invoice(amount=750),   # will be partial
            _make_invoice(amount=600),   # pending 600
        ]
        invoices[0].record_payment(500, PaymentMethod.CASH)
        invoices[1].record_payment(200, PaymentMethod.CASH)

        total_pending = sum(inv.pending_amount for inv in invoices)
        assert total_pending == Decimal("1150")

    def test_mark_overdue(self):
        inv = _make_invoice(due_date=date.today() - timedelta(days=10))
        inv.mark_overdue()
        assert inv.status == InvoiceStatus.OVERDUE

        events = [e for e in inv.domain_events if e.__class__.__name__ == "InvoiceOverdue"]
        assert len(events) == 1
        assert events[0].days_overdue == 10

    def test_mark_overdue_no_op_for_paid(self):
        inv = _make_invoice(amount=100)
        inv.record_payment(100, PaymentMethod.CASH)
        inv.mark_overdue()
        assert inv.status == InvoiceStatus.PAID
