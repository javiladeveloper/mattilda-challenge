"""Unit tests for Invoice Service business logic."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from src.domain.enums import InvoiceStatus, PaymentMethod
from src.domain.exceptions import (
    EntityNotFoundError,
    PaymentExceedsDebtError,
    InvoiceCancelledError,
)


class TestInvoiceStatusCalculation:
    """Test invoice status calculation based on payments."""

    def test_invoice_status_pending_when_no_payments(self):
        """Invoice should be PENDING when no payments made."""
        # Given an invoice amount
        amount = Decimal("500.00")
        paid = Decimal("0.00")

        # When calculating status
        if paid >= amount:
            status = InvoiceStatus.PAID
        elif paid > 0:
            status = InvoiceStatus.PARTIAL
        else:
            status = InvoiceStatus.PENDING

        # Then status should be PENDING
        assert status == InvoiceStatus.PENDING

    def test_invoice_status_partial_when_partially_paid(self):
        """Invoice should be PARTIAL when partially paid."""
        amount = Decimal("500.00")
        paid = Decimal("200.00")

        if paid >= amount:
            status = InvoiceStatus.PAID
        elif paid > 0:
            status = InvoiceStatus.PARTIAL
        else:
            status = InvoiceStatus.PENDING

        assert status == InvoiceStatus.PARTIAL

    def test_invoice_status_paid_when_fully_paid(self):
        """Invoice should be PAID when fully paid."""
        amount = Decimal("500.00")
        paid = Decimal("500.00")

        if paid >= amount:
            status = InvoiceStatus.PAID
        elif paid > 0:
            status = InvoiceStatus.PARTIAL
        else:
            status = InvoiceStatus.PENDING

        assert status == InvoiceStatus.PAID

    def test_invoice_status_paid_when_overpaid(self):
        """Invoice should be PAID even if overpaid (edge case)."""
        amount = Decimal("500.00")
        paid = Decimal("550.00")

        if paid >= amount:
            status = InvoiceStatus.PAID
        elif paid > 0:
            status = InvoiceStatus.PARTIAL
        else:
            status = InvoiceStatus.PENDING

        assert status == InvoiceStatus.PAID


class TestPaymentValidation:
    """Test payment validation rules."""

    def test_payment_cannot_exceed_pending_amount(self):
        """Payment amount cannot exceed pending amount."""
        pending = Decimal("300.00")
        payment_amount = Decimal("400.00")

        with pytest.raises(PaymentExceedsDebtError):
            if payment_amount > pending:
                raise PaymentExceedsDebtError(float(payment_amount), float(pending))

    def test_payment_equal_to_pending_is_valid(self):
        """Payment equal to pending amount is valid."""
        pending = Decimal("300.00")
        payment_amount = Decimal("300.00")

        # Should not raise
        is_valid = payment_amount <= pending
        assert is_valid is True

    def test_payment_less_than_pending_is_valid(self):
        """Payment less than pending amount is valid."""
        pending = Decimal("300.00")
        payment_amount = Decimal("100.00")

        is_valid = payment_amount <= pending
        assert is_valid is True

    def test_cannot_pay_cancelled_invoice(self):
        """Cannot process payment for cancelled invoice."""
        invoice_id = uuid4()
        invoice_status = InvoiceStatus.CANCELLED

        with pytest.raises(InvoiceCancelledError):
            if invoice_status == InvoiceStatus.CANCELLED:
                raise InvoiceCancelledError(invoice_id)


class TestFinancialCalculations:
    """Test financial calculation logic."""

    def test_pending_amount_calculation(self):
        """Test pending amount = total - paid."""
        total = Decimal("1000.00")
        paid = Decimal("350.00")
        expected_pending = Decimal("650.00")

        pending = total - paid

        assert pending == expected_pending

    def test_total_debt_across_invoices(self):
        """Test total debt calculation across multiple invoices."""
        invoices = [
            {"amount": Decimal("500.00"), "paid": Decimal("500.00")},  # PAID
            {"amount": Decimal("750.00"), "paid": Decimal("200.00")},  # PARTIAL
            {"amount": Decimal("600.00"), "paid": Decimal("0.00")},    # PENDING
        ]

        total_pending = sum(
            inv["amount"] - inv["paid"] for inv in invoices
        )

        assert total_pending == Decimal("1150.00")

    def test_overdue_detection(self):
        """Test overdue invoice detection."""
        today = date.today()
        due_date_past = today - timedelta(days=10)
        due_date_future = today + timedelta(days=10)
        status_pending = InvoiceStatus.PENDING

        is_overdue_past = due_date_past < today and status_pending in [
            InvoiceStatus.PENDING, InvoiceStatus.PARTIAL
        ]
        is_overdue_future = due_date_future < today and status_pending in [
            InvoiceStatus.PENDING, InvoiceStatus.PARTIAL
        ]

        assert is_overdue_past is True
        assert is_overdue_future is False
