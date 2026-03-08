from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from src.domain.entities.student import Student
from src.domain.interfaces.unit_of_work import UnitOfWork
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus
from src.application.dto.statements import (
    StudentStatementDTO,
    InvoiceSummaryDTO,
    PaymentSummaryDTO,
    FinancialSummaryDTO,
)


class StudentService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_all(
        self, skip: int = 0, limit: int = 100, school_id: UUID = None, active_only: bool = False
    ) -> List[Student]:
        if school_id:
            return await self._uow.students.get_by_school(
                school_id, skip=skip, limit=limit, active_only=active_only
            )
        filters = {"is_active": True} if active_only else None
        return await self._uow.students.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_id(self, student_id: UUID) -> Student:
        student = await self._uow.students.get_by_id(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)
        return student

    async def create(self, data: dict) -> Student:
        school = await self._uow.schools.get_by_id(data.get("school_id"))
        if not school:
            raise EntityNotFoundError("School", data.get("school_id"))

        student = Student(**data)
        saved = await self._uow.students.save(student)
        self._uow.track(student)
        await self._uow.commit()
        return saved

    async def update(self, student_id: UUID, data: dict) -> Student:
        student = await self._uow.students.get_by_id(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)

        if "school_id" in data:
            school = await self._uow.schools.get_by_id(data["school_id"])
            if not school:
                raise EntityNotFoundError("School", data["school_id"])

        student.update(**data)
        saved = await self._uow.students.save(student)
        self._uow.track(student)
        await self._uow.commit()
        return saved

    async def delete(self, student_id: UUID) -> Student:
        student = await self._uow.students.get_by_id(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)
        student.deactivate()
        saved = await self._uow.students.save(student)
        self._uow.track(student)
        await self._uow.commit()
        return saved

    async def count(self, school_id: UUID = None, active_only: bool = False) -> int:
        filters = {}
        if school_id:
            filters["school_id"] = school_id
        if active_only:
            filters["is_active"] = True
        return await self._uow.students.count(filters if filters else None)

    async def get_statement(self, student_id: UUID) -> StudentStatementDTO:
        student = await self._uow.students.get_by_id(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)

        await self._uow.invoices.update_overdue_status()
        await self._uow.commit()

        school = await self._uow.schools.get_by_id(student.school_id)
        invoices = await self._uow.invoices.get_by_student(student_id, limit=1000)

        total_invoiced = Decimal("0")
        total_paid = Decimal("0")
        total_pending = Decimal("0")
        total_overdue = Decimal("0")

        invoice_summaries = []
        for inv in invoices:
            if inv.status == InvoiceStatus.CANCELLED:
                continue

            total_invoiced += inv.amount
            total_paid += inv.paid_amount

            if inv.status == InvoiceStatus.OVERDUE:
                total_overdue += inv.pending_amount
            elif inv.status in (InvoiceStatus.PENDING, InvoiceStatus.PARTIAL):
                total_pending += inv.pending_amount

            payments = [
                PaymentSummaryDTO(
                    amount=p.amount,
                    date=p.payment_date,
                    method=p.method,
                )
                for p in inv.payments
            ]

            invoice_summaries.append(
                InvoiceSummaryDTO(
                    id=inv.id,
                    description=inv.description,
                    amount=inv.amount,
                    paid_amount=inv.paid_amount,
                    pending_amount=inv.pending_amount,
                    status=inv.status,
                    due_date=inv.due_date,
                    payments=payments,
                )
            )

        return StudentStatementDTO(
            student_id=student.id,
            student_name=student.full_name,
            school_name=school.name if school else "Unknown",
            summary=FinancialSummaryDTO(
                total_invoiced=total_invoiced,
                total_paid=total_paid,
                total_pending=total_pending,
                total_overdue=total_overdue,
            ),
            invoices=invoice_summaries,
            generated_at=datetime.utcnow(),
        )
