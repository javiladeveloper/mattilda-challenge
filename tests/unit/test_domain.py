"""Unit tests for domain layer: entities, value objects, and business rules.

These tests verify domain logic in isolation — no database, no HTTP, no I/O.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from src.domain.entities.invoice import Invoice, Payment
from src.domain.entities.school import School
from src.domain.entities.student import Student
from src.domain.enums import InvoiceStatus, PaymentMethod
from src.domain.events import (
    PaymentRecorded,
    InvoicePaid,
    InvoiceCancelled,
    InvoiceOverdue,
    SchoolDeactivated,
    StudentDeactivated,
)
from src.domain.exceptions import (
    BusinessRuleError,
    EntityNotFoundError,
    InvoiceCancelledError,
    PaymentExceedsDebtError,
    ValidationError,
)
from src.domain.value_objects import Money, EmailAddress, FullName


# ============================================================
# Value Objects
# ============================================================


class TestMoney:
    def test_creation(self):
        m = Money(100)
        assert m.to_decimal() == Decimal("100.00")

    def test_rounds_to_cents(self):
        m = Money("99.999")
        assert m.to_decimal() == Decimal("100.00")

    def test_negative_raises(self):
        with pytest.raises(ValidationError):
            Money(-1)

    def test_zero_is_valid(self):
        m = Money(0)
        assert m.is_zero()

    def test_addition(self):
        assert Money(10) + Money(20) == Money(30)

    def test_subtraction(self):
        assert Money(30) - Money(10) == Money(20)

    def test_subtraction_negative_raises(self):
        with pytest.raises(ValidationError):
            Money(10) - Money(20)

    def test_comparison(self):
        assert Money(10) < Money(20)
        assert Money(20) > Money(10)
        assert Money(10) == Money(10)
        assert Money(10) >= Money(10)
        assert Money(10) <= Money(10)

    def test_immutable(self):
        m = Money(100)
        with pytest.raises(AttributeError):
            m.value = 200

    def test_zero_constant(self):
        assert Money.ZERO.is_zero()
        assert Money.ZERO == Money(0)


class TestEmailAddress:
    def test_valid_email(self):
        email = EmailAddress("user@example.com")
        assert email.value == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            EmailAddress("not-an-email")

    def test_empty_email_raises(self):
        with pytest.raises(ValidationError):
            EmailAddress("")

    def test_immutable(self):
        email = EmailAddress("user@example.com")
        with pytest.raises(AttributeError):
            email.something = "x"

    def test_equality(self):
        assert EmailAddress("a@b.com") == EmailAddress("a@b.com")
        assert EmailAddress("a@b.com") != EmailAddress("x@y.com")

    def test_lowercases(self):
        assert EmailAddress("User@Example.COM").value == "user@example.com"


class TestFullName:
    def test_valid_name(self):
        name = FullName("John", "Doe")
        assert name.first_name == "John"
        assert name.last_name == "Doe"
        assert name.full == "John Doe"

    def test_empty_first_name_raises(self):
        with pytest.raises(ValidationError):
            FullName("", "Doe")

    def test_empty_last_name_raises(self):
        with pytest.raises(ValidationError):
            FullName("John", "")

    def test_strips_whitespace(self):
        name = FullName("  John  ", "  Doe  ")
        assert name.first_name == "John"
        assert name.last_name == "Doe"

    def test_immutable(self):
        name = FullName("John", "Doe")
        with pytest.raises(AttributeError):
            name.value = "x"

    def test_equality(self):
        assert FullName("John", "Doe") == FullName("John", "Doe")
        assert FullName("John", "Doe") != FullName("Jane", "Doe")


# ============================================================
# School Entity
# ============================================================


class TestSchool:
    def test_creation(self):
        school = School(name="Test School")
        assert school.name == "Test School"
        assert school.is_active is True
        assert school.id is not None

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            School(name="")

    def test_validates_email(self):
        with pytest.raises(ValidationError):
            School(name="School", email="not-valid")

    def test_accepts_valid_email(self):
        school = School(name="School", email="admin@school.com")
        assert school.email == "admin@school.com"

    def test_accepts_no_email(self):
        school = School(name="School")
        assert school.email is None

    def test_deactivate(self):
        school = School(name="School")
        school.deactivate()
        assert school.is_active is False

    def test_deactivate_already_inactive_raises(self):
        school = School(name="School", is_active=False)
        with pytest.raises(BusinessRuleError):
            school.deactivate()

    def test_deactivate_emits_event(self):
        school = School(name="School")
        school.deactivate()
        assert len(school.domain_events) == 1
        assert isinstance(school.domain_events[0], SchoolDeactivated)
        assert school.domain_events[0].school_id == school.id

    def test_update(self):
        school = School(name="Old Name")
        school.update(name="New Name", phone="123456")
        assert school.name == "New Name"
        assert school.phone == "123456"

    def test_update_invalid_field_raises(self):
        school = School(name="School")
        with pytest.raises(ValidationError):
            school.update(nonexistent="value")

    def test_clear_events(self):
        school = School(name="School")
        school.deactivate()
        assert len(school.domain_events) == 1
        school.clear_events()
        assert len(school.domain_events) == 0


# ============================================================
# Student Entity
# ============================================================


class TestStudent:
    def test_creation(self):
        student = Student(
            first_name="John", last_name="Doe", school_id=uuid4()
        )
        assert student.first_name == "John"
        assert student.last_name == "Doe"
        assert student.full_name == "John Doe"
        assert student.is_active is True

    def test_name_value_object(self):
        student = Student(
            first_name="John", last_name="Doe", school_id=uuid4()
        )
        assert isinstance(student.name, FullName)
        assert student.name.full == "John Doe"

    def test_empty_first_name_raises(self):
        with pytest.raises(ValidationError):
            Student(first_name="", last_name="Doe", school_id=uuid4())

    def test_validates_email(self):
        with pytest.raises(ValidationError):
            Student(
                first_name="John", last_name="Doe",
                school_id=uuid4(), email="not-valid"
            )

    def test_deactivate(self):
        student = Student(
            first_name="John", last_name="Doe", school_id=uuid4()
        )
        student.deactivate()
        assert student.is_active is False

    def test_deactivate_emits_event(self):
        school_id = uuid4()
        student = Student(
            first_name="John", last_name="Doe", school_id=school_id
        )
        student.deactivate()
        assert len(student.domain_events) == 1
        assert isinstance(student.domain_events[0], StudentDeactivated)
        assert student.domain_events[0].school_id == school_id

    def test_update_name(self):
        student = Student(
            first_name="John", last_name="Doe", school_id=uuid4()
        )
        student.update(first_name="Jane")
        assert student.first_name == "Jane"
        assert student.last_name == "Doe"

    def test_update_both_names(self):
        student = Student(
            first_name="John", last_name="Doe", school_id=uuid4()
        )
        student.update(first_name="Jane", last_name="Smith")
        assert student.full_name == "Jane Smith"


# ============================================================
# Invoice Aggregate Root
# ============================================================


class TestInvoice:
    def _make_invoice(self, amount=1000, **kwargs):
        return Invoice(
            student_id=uuid4(),
            amount=amount,
            due_date=date.today() + timedelta(days=30),
            **kwargs,
        )

    def test_creation(self):
        inv = self._make_invoice()
        assert inv.amount == Decimal("1000.00")
        assert inv.status == InvoiceStatus.PENDING
        assert inv.paid_amount == Decimal("0")
        assert inv.pending_amount == Decimal("1000.00")
        assert inv.payments == []

    def test_zero_amount_raises(self):
        with pytest.raises(BusinessRuleError):
            self._make_invoice(amount=0)

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            self._make_invoice(amount=-100)

    def test_record_payment_partial(self):
        inv = self._make_invoice(amount=1000)
        payment = inv.record_payment(300, PaymentMethod.CASH)

        assert payment.amount == Decimal("300.00")
        assert inv.paid_amount == Decimal("300.00")
        assert inv.pending_amount == Decimal("700.00")
        assert inv.status == InvoiceStatus.PARTIAL
        assert len(inv.payments) == 1

    def test_record_payment_full(self):
        inv = self._make_invoice(amount=500)
        inv.record_payment(500, PaymentMethod.BANK_TRANSFER)

        assert inv.status == InvoiceStatus.PAID
        assert inv.pending_amount == Decimal("0")

    def test_record_multiple_payments(self):
        inv = self._make_invoice(amount=1000)
        inv.record_payment(300, PaymentMethod.CASH)
        inv.record_payment(400, PaymentMethod.CASH)
        inv.record_payment(300, PaymentMethod.BANK_TRANSFER)

        assert inv.status == InvoiceStatus.PAID
        assert inv.paid_amount == Decimal("1000.00")
        assert len(inv.payments) == 3

    def test_payment_exceeds_pending_raises(self):
        inv = self._make_invoice(amount=500)
        with pytest.raises(PaymentExceedsDebtError):
            inv.record_payment(600, PaymentMethod.CASH)

    def test_payment_on_cancelled_raises(self):
        inv = self._make_invoice()
        inv.cancel()
        with pytest.raises(InvoiceCancelledError):
            inv.record_payment(100, PaymentMethod.CASH)

    def test_cancel(self):
        inv = self._make_invoice()
        inv.cancel()
        assert inv.status == InvoiceStatus.CANCELLED

    def test_cancel_already_cancelled_raises(self):
        inv = self._make_invoice()
        inv.cancel()
        with pytest.raises(BusinessRuleError, match="already cancelled"):
            inv.cancel()

    def test_cancel_with_payments_raises(self):
        inv = self._make_invoice(amount=1000)
        inv.record_payment(100, PaymentMethod.CASH)
        with pytest.raises(BusinessRuleError, match="Cannot cancel"):
            inv.cancel()

    def test_mark_overdue(self):
        inv = Invoice(
            student_id=uuid4(),
            amount=500,
            due_date=date.today() - timedelta(days=10),
        )
        inv.mark_overdue()
        assert inv.status == InvoiceStatus.OVERDUE

    def test_mark_overdue_paid_invoice_no_change(self):
        inv = self._make_invoice(amount=500)
        inv.record_payment(500, PaymentMethod.CASH)
        inv.mark_overdue()
        assert inv.status == InvoiceStatus.PAID

    def test_update_details(self):
        inv = self._make_invoice(amount=1000)
        new_date = date.today() + timedelta(days=60)
        inv.update_details(amount=2000, due_date=new_date, description="Updated")
        assert inv.amount == Decimal("2000.00")
        assert inv.due_date == new_date
        assert inv.description == "Updated"

    def test_update_details_below_paid_raises(self):
        inv = self._make_invoice(amount=1000)
        inv.record_payment(600, PaymentMethod.CASH)
        with pytest.raises(BusinessRuleError, match="Cannot reduce amount"):
            inv.update_details(amount=500)

    def test_update_details_cancelled_raises(self):
        inv = self._make_invoice()
        inv.cancel()
        with pytest.raises(BusinessRuleError, match="cancelled"):
            inv.update_details(description="nope")


# ============================================================
# Domain Events
# ============================================================


class TestInvoiceDomainEvents:
    def _make_invoice(self, amount=1000, **kwargs):
        return Invoice(
            student_id=uuid4(),
            amount=amount,
            due_date=date.today() + timedelta(days=30),
            **kwargs,
        )

    def test_record_payment_emits_event(self):
        inv = self._make_invoice()
        inv.record_payment(300, PaymentMethod.CASH)

        events = inv.domain_events
        assert len(events) == 1
        assert isinstance(events[0], PaymentRecorded)
        assert events[0].amount == Decimal("300.00")
        assert events[0].new_status == "PARTIAL"

    def test_full_payment_emits_paid_event(self):
        inv = self._make_invoice(amount=500)
        inv.record_payment(500, PaymentMethod.CASH)

        events = inv.domain_events
        assert len(events) == 2
        assert isinstance(events[0], PaymentRecorded)
        assert isinstance(events[1], InvoicePaid)
        assert events[1].amount == Decimal("500.00")

    def test_cancel_emits_event(self):
        inv = self._make_invoice()
        inv.cancel()

        events = inv.domain_events
        assert len(events) == 1
        assert isinstance(events[0], InvoiceCancelled)
        assert events[0].invoice_id == inv.id

    def test_mark_overdue_emits_event(self):
        inv = Invoice(
            student_id=uuid4(),
            amount=500,
            due_date=date.today() - timedelta(days=5),
        )
        inv.mark_overdue()

        events = inv.domain_events
        assert len(events) == 1
        assert isinstance(events[0], InvoiceOverdue)
        assert events[0].days_overdue == 5

    def test_clear_events(self):
        inv = self._make_invoice()
        inv.record_payment(100, PaymentMethod.CASH)
        assert len(inv.domain_events) == 1
        inv.clear_events()
        assert len(inv.domain_events) == 0


# ============================================================
# Payment Entity
# ============================================================


class TestPayment:
    def test_creation(self):
        p = Payment(
            invoice_id=uuid4(),
            amount=500,
            method=PaymentMethod.CASH,
        )
        assert p.amount == Decimal("500.00")
        assert p.method == PaymentMethod.CASH

    def test_zero_amount_raises(self):
        with pytest.raises(BusinessRuleError):
            Payment(invoice_id=uuid4(), amount=0, method=PaymentMethod.CASH)

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            Payment(invoice_id=uuid4(), amount=-10, method=PaymentMethod.CASH)


# ============================================================
# Enums
# ============================================================


class TestInvoiceStatusEnum:
    def test_all_statuses_exist(self):
        assert InvoiceStatus.PENDING == "PENDING"
        assert InvoiceStatus.PARTIAL == "PARTIAL"
        assert InvoiceStatus.PAID == "PAID"
        assert InvoiceStatus.OVERDUE == "OVERDUE"
        assert InvoiceStatus.CANCELLED == "CANCELLED"

    def test_status_count(self):
        assert len(InvoiceStatus) == 5


class TestPaymentMethodEnum:
    def test_all_methods_exist(self):
        assert PaymentMethod.CASH == "CASH"
        assert PaymentMethod.BANK_TRANSFER == "BANK_TRANSFER"
        assert PaymentMethod.CREDIT_CARD == "CREDIT_CARD"
        assert PaymentMethod.DEBIT_CARD == "DEBIT_CARD"
        assert PaymentMethod.OTHER == "OTHER"

    def test_method_count(self):
        assert len(PaymentMethod) == 5


# ============================================================
# Exceptions
# ============================================================


class TestExceptions:
    def test_entity_not_found_error(self):
        error = EntityNotFoundError("School", "123")
        assert "School" in error.message
        assert "123" in error.message

    def test_payment_exceeds_debt_error(self):
        error = PaymentExceedsDebtError(500.00, 300.00)
        assert "500" in error.message
        assert "300" in error.message
        assert error.details["rule"] == "payment_cannot_exceed_debt"

    def test_invoice_cancelled_error(self):
        error = InvoiceCancelledError("inv-123")
        assert "inv-123" in error.message
        assert error.details["rule"] == "no_payment_for_cancelled_invoice"
