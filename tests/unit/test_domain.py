"""Unit tests for domain entities and enums."""

import pytest
from decimal import Decimal

from src.domain.enums import InvoiceStatus, PaymentMethod
from src.domain.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    PaymentExceedsDebtError,
    InvoiceCancelledError,
)


class TestInvoiceStatusEnum:
    """Test InvoiceStatus enum values."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        assert InvoiceStatus.PENDING == "PENDING"
        assert InvoiceStatus.PARTIAL == "PARTIAL"
        assert InvoiceStatus.PAID == "PAID"
        assert InvoiceStatus.OVERDUE == "OVERDUE"
        assert InvoiceStatus.CANCELLED == "CANCELLED"

    def test_status_count(self):
        """Should have exactly 5 statuses."""
        assert len(InvoiceStatus) == 5


class TestPaymentMethodEnum:
    """Test PaymentMethod enum values."""

    def test_all_methods_exist(self):
        """All expected payment methods should exist."""
        assert PaymentMethod.CASH == "CASH"
        assert PaymentMethod.BANK_TRANSFER == "BANK_TRANSFER"
        assert PaymentMethod.CREDIT_CARD == "CREDIT_CARD"
        assert PaymentMethod.DEBIT_CARD == "DEBIT_CARD"
        assert PaymentMethod.OTHER == "OTHER"

    def test_method_count(self):
        """Should have exactly 5 methods."""
        assert len(PaymentMethod) == 5


class TestExceptions:
    """Test custom domain exceptions."""

    def test_entity_not_found_error(self):
        """EntityNotFoundError should contain entity info."""
        error = EntityNotFoundError("School", "123")

        assert "School" in error.message
        assert "123" in error.message
        assert error.details["entity"] == "School"
        assert error.details["id"] == "123"

    def test_validation_error(self):
        """ValidationError should contain field info."""
        error = ValidationError("Invalid email format", field="email")

        assert error.message == "Invalid email format"
        assert error.details["field"] == "email"

    def test_validation_error_without_field(self):
        """ValidationError can be created without field."""
        error = ValidationError("General validation error")

        assert error.message == "General validation error"
        assert error.details is None

    def test_business_rule_error(self):
        """BusinessRuleError should contain rule info."""
        error = BusinessRuleError("Cannot delete active school", rule="no_delete_active")

        assert error.message == "Cannot delete active school"
        assert error.details["rule"] == "no_delete_active"

    def test_payment_exceeds_debt_error(self):
        """PaymentExceedsDebtError should show amounts."""
        error = PaymentExceedsDebtError(500.00, 300.00)

        assert "500" in error.message
        assert "300" in error.message
        assert error.details["rule"] == "payment_cannot_exceed_debt"

    def test_invoice_cancelled_error(self):
        """InvoiceCancelledError should show invoice id."""
        error = InvoiceCancelledError("inv-123")

        assert "inv-123" in error.message
        assert error.details["rule"] == "no_payment_for_cancelled_invoice"
