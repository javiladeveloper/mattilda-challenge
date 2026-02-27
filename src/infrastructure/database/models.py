"""
SQLAlchemy ORM Models for Mattilda Backend.

This module defines the database schema using SQLAlchemy 2.0 with async support.
All models use UUID as primary keys for better distribution and security.

Database Design Decisions:
- UUIDs: Better for distributed systems, no sequential guessing
- Soft Deletes: is_active flag instead of hard deletes for audit trail
- Timestamps: created_at and updated_at for all entities
- Decimal: Numeric(12,2) for monetary values (up to 9,999,999,999.99)
- Relationships: Lazy loading with selectin for performance optimization

Entity Relationships:
- School 1:N Student (one school has many students)
- Student 1:N Invoice (one student has many invoices)
- Invoice 1:N Payment (one invoice can have multiple payments)
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.domain.enums import InvoiceStatus, PaymentMethod


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class School(Base):
    """
    School entity representing an educational institution.

    This is the top-level entity in the hierarchy. Each school can have
    multiple students enrolled, and through students, multiple invoices.

    Attributes:
        id: Unique identifier (UUID v4)
        name: School name (required, max 255 chars)
        address: Physical address (optional)
        phone: Contact phone number (optional)
        email: Contact email address (optional)
        is_active: Soft delete flag (default True)
        created_at: Record creation timestamp (auto-set)
        updated_at: Last modification timestamp (auto-updated)
        students: Relationship to Student entities

    Indexes:
        - Primary key on id
        - Index on is_active for filtering active schools
        - Index on name for search queries

    Business Rules:
        - School cannot be hard deleted if it has students
        - Deactivating a school does not deactivate its students
    """
    __tablename__ = "schools"
    __table_args__ = (
        Index("ix_schools_is_active", "is_active"),
        Index("ix_schools_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the school"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of the educational institution"
    )
    address: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Physical address of the school"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Contact phone number"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email address"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Soft delete flag: False means logically deleted"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the record was last updated"
    )

    # Relationships
    students: Mapped[List["Student"]] = relationship(
        "Student",
        back_populates="school",
        lazy="selectin",
        doc="List of students enrolled in this school"
    )

    def __repr__(self) -> str:
        return f"<School(id={self.id}, name='{self.name}')>"


class Student(Base):
    """
    Student entity representing an enrolled student in a school.

    Students belong to exactly one school and can have multiple invoices
    for tuition, fees, and other charges.

    Attributes:
        id: Unique identifier (UUID v4)
        school_id: Foreign key to schools table (required)
        first_name: Student's first name (required, max 100 chars)
        last_name: Student's last name (required, max 100 chars)
        email: Student or parent email (optional)
        grade: Current grade/level (optional, e.g., "5th Grade", "High School")
        enrolled_at: Date when student was enrolled (default: today)
        is_active: Soft delete flag (default True)
        created_at: Record creation timestamp (auto-set)
        updated_at: Last modification timestamp (auto-updated)
        school: Relationship to parent School entity
        invoices: Relationship to Invoice entities

    Indexes:
        - Primary key on id
        - Foreign key index on school_id
        - Index on is_active for filtering
        - Composite index on (school_id, is_active) for school queries

    Computed Properties:
        - full_name: Concatenation of first_name and last_name

    Business Rules:
        - Student must belong to an existing school
        - Deactivating a student does not affect their invoices
        - Student's financial summary includes all non-cancelled invoices
    """
    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_school_id", "school_id"),
        Index("ix_students_is_active", "is_active"),
        Index("ix_students_school_active", "school_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the student"
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the school where student is enrolled"
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Student's first name"
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Student's last name"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Student or parent/guardian email"
    )
    grade: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Current grade or level (e.g., '5th Grade', 'Senior')"
    )
    enrolled_at: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        comment="Date when the student was enrolled"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Soft delete flag: False means student has withdrawn"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the record was last updated"
    )

    # Relationships
    school: Mapped["School"] = relationship(
        "School",
        back_populates="students",
        doc="The school where this student is enrolled"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="student",
        lazy="selectin",
        doc="List of invoices for this student"
    )

    @property
    def full_name(self) -> str:
        """Return the student's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name='{self.full_name}')>"


class Invoice(Base):
    """
    Invoice entity representing a billing document for a student.

    Invoices track charges for tuition, fees, materials, etc. Each invoice
    can have multiple payments (partial payments are allowed).

    Attributes:
        id: Unique identifier (UUID v4)
        student_id: Foreign key to students table (required)
        amount: Total invoice amount (required, Decimal with 2 decimals)
        due_date: Payment due date (required)
        status: Current invoice status (InvoiceStatus enum)
        description: Description of the charge (optional)
        created_at: Record creation timestamp (auto-set)
        updated_at: Last modification timestamp (auto-updated)
        student: Relationship to parent Student entity
        payments: Relationship to Payment entities

    Indexes:
        - Primary key on id
        - Foreign key index on student_id
        - Index on status for filtering
        - Index on due_date for overdue queries
        - Composite index on (student_id, status) for student queries

    Computed Properties:
        - paid_amount: Sum of all payment amounts
        - pending_amount: amount - paid_amount

    Status Values (InvoiceStatus enum):
        - PENDING: No payments made yet
        - PARTIAL: Some payments made, balance remaining
        - PAID: Fully paid (paid_amount >= amount)
        - OVERDUE: Past due_date and not fully paid
        - CANCELLED: Invoice voided (no payments accepted)

    Business Rules:
        - Invoice amount must be positive
        - Payments cannot exceed pending_amount
        - Cancelled invoices cannot receive payments
        - Status auto-updates based on payments
    """
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_student_id", "student_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
        Index("ix_invoices_student_status", "student_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the invoice"
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the student being billed"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total invoice amount (max: 9,999,999,999.99)"
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Payment due date"
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        String(20),
        default=InvoiceStatus.PENDING,
        comment="Invoice status: PENDING, PARTIAL, PAID, OVERDUE, CANCELLED"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the charge (e.g., 'March 2024 Tuition')"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the invoice was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the invoice was last updated"
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        "Student",
        back_populates="invoices",
        doc="The student this invoice belongs to"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        lazy="selectin",
        doc="List of payments made against this invoice"
    )

    @property
    def paid_amount(self) -> Decimal:
        """Calculate total amount paid for this invoice."""
        return sum((p.amount for p in self.payments), Decimal("0"))

    @property
    def pending_amount(self) -> Decimal:
        """Calculate remaining amount to be paid."""
        return self.amount - self.paid_amount

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, amount={self.amount}, status={self.status})>"


class Payment(Base):
    """
    Payment entity representing a payment transaction against an invoice.

    Payments record actual money received. Multiple payments can be made
    against a single invoice (partial payments).

    Attributes:
        id: Unique identifier (UUID v4)
        invoice_id: Foreign key to invoices table (required)
        amount: Payment amount (required, Decimal with 2 decimals)
        payment_date: Date payment was received (default: today)
        method: Payment method (PaymentMethod enum)
        reference: External reference number (optional, e.g., check #)
        created_at: Record creation timestamp (auto-set)
        invoice: Relationship to parent Invoice entity

    Indexes:
        - Primary key on id
        - Foreign key index on invoice_id
        - Index on payment_date for date range queries
        - Index on method for payment method reports

    Payment Methods (PaymentMethod enum):
        - CASH: Cash payment
        - BANK_TRANSFER: Wire transfer or ACH
        - CREDIT_CARD: Credit card payment
        - DEBIT_CARD: Debit card payment
        - OTHER: Other payment methods

    Business Rules:
        - Payment amount must be positive
        - Payment amount cannot exceed invoice pending_amount
        - Payments cannot be made to CANCELLED invoices
        - Payments are immutable (no updates or deletes)
        - Creating a payment auto-updates invoice status

    Note:
        Payments do not have updated_at because they are immutable.
        Once recorded, a payment cannot be modified - only reversed
        through a separate adjustment process (not implemented).
    """
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_payment_date", "payment_date"),
        Index("ix_payments_method", "method"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the payment"
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to the invoice being paid"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Payment amount (must be positive)"
    )
    payment_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        comment="Date when payment was received"
    )
    method: Mapped[PaymentMethod] = mapped_column(
        String(20),
        default=PaymentMethod.CASH,
        comment="Payment method: CASH, BANK_TRANSFER, CREDIT_CARD, DEBIT_CARD, OTHER"
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="External reference (check number, transaction ID, etc.)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when the payment was recorded"
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="payments",
        doc="The invoice this payment is applied to"
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, method={self.method})>"


# Note: User model is defined in models_user.py to avoid circular imports
