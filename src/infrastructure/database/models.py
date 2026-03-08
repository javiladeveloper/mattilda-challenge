"""
SQLAlchemy ORM Models for Mattilda Backend.

This module defines the database schema using SQLAlchemy 2.0 with async support.
All models use UUID as primary keys for better distribution and security.

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
    pass


class School(Base):
    __tablename__ = "schools"
    __table_args__ = (
        Index("ix_schools_is_active", "is_active"),
        Index("ix_schools_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="school", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<School(id={self.id}, name='{self.name}')>"


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_school_id", "school_id"),
        Index("ix_students_is_active", "is_active"),
        Index("ix_students_school_active", "school_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="RESTRICT"), nullable=False,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enrolled_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    school: Mapped["School"] = relationship("School", back_populates="students")
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice", back_populates="student", lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, name='{self.full_name}')>"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_student_id", "student_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
        Index("ix_invoices_student_status", "student_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="RESTRICT"), nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        String(20), default=InvoiceStatus.PENDING,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="invoices")
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="invoice", lazy="selectin",
    )

    @property
    def paid_amount(self) -> Decimal:
        return sum((p.amount for p in self.payments), Decimal("0"))

    @property
    def pending_amount(self) -> Decimal:
        return self.amount - self.paid_amount

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, amount={self.amount}, status={self.status})>"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_payment_date", "payment_date"),
        Index("ix_payments_method", "method"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    method: Mapped[PaymentMethod] = mapped_column(
        String(20), default=PaymentMethod.CASH,
    )
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, amount={self.amount}, method={self.method})>"
