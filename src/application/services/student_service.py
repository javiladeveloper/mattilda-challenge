from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Student
from src.infrastructure.database.repositories import (
    StudentRepository,
    SchoolRepository,
    GradeRepository,
)
from src.domain.exceptions import EntityNotFoundError, BusinessRuleError
from src.domain.enums import InvoiceStatus
from src.application.dto.statements import (
    StudentStatementDTO,
    InvoiceSummaryDTO,
    PaymentSummaryDTO,
    FinancialSummaryDTO,
)


class StudentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StudentRepository(session)
        self.school_repo = SchoolRepository(session)
        self.grade_repo = GradeRepository(session)

    async def get_all(
        self, skip: int = 0, limit: int = 100, school_id: UUID = None, active_only: bool = False
    ) -> List[Student]:
        if school_id:
            return await self.repo.get_by_school(
                school_id, skip=skip, limit=limit, active_only=active_only
            )
        filters = {"is_active": True} if active_only else None
        return await self.repo.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_id(self, student_id: UUID) -> Student:
        student = await self.repo.get_by_id(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)
        return student

    async def get_with_invoices(self, student_id: UUID) -> Student:
        """Get student with all invoices and payments loaded."""
        student = await self.repo.get_with_invoices(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)
        return student

    async def create(self, data: dict) -> Student:
        school_id = data.get("school_id")
        grade_id = data.get("grade_id")

        # Verify school exists
        school = await self.school_repo.get_by_id(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)

        # Verify grade exists and belongs to the same school
        if grade_id:
            grade = await self.grade_repo.get_by_id(grade_id)
            if not grade:
                raise EntityNotFoundError("Grade", grade_id)
            if grade.school_id != school_id:
                raise BusinessRuleError(f"Grade {grade_id} does not belong to school {school_id}")

        return await self.repo.create(data)

    async def update(self, student_id: UUID, data: dict) -> Student:
        # Get current student to check school
        current_student = await self.repo.get_by_id(student_id)
        if not current_student:
            raise EntityNotFoundError("Student", student_id)

        # Determine the school_id (new one if updating, or existing one)
        school_id = data.get("school_id", current_student.school_id)

        # If school_id is being updated, verify new school exists
        if "school_id" in data:
            school = await self.school_repo.get_by_id(school_id)
            if not school:
                raise EntityNotFoundError("School", school_id)

        # If grade_id is being updated, verify it exists and belongs to the school
        if "grade_id" in data and data["grade_id"] is not None:
            grade = await self.grade_repo.get_by_id(data["grade_id"])
            if not grade:
                raise EntityNotFoundError("Grade", data["grade_id"])
            if grade.school_id != school_id:
                raise BusinessRuleError(
                    f"Grade {data['grade_id']} does not belong to school {school_id}"
                )

        student = await self.repo.update(student_id, data)
        return student

    async def delete(self, student_id: UUID) -> Student:
        student = await self.repo.soft_delete(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)
        return student

    async def count(self, school_id: UUID = None, active_only: bool = False) -> int:
        filters = {}
        if school_id:
            filters["school_id"] = school_id
        if active_only:
            filters["is_active"] = True
        return await self.repo.count(filters if filters else None)

    async def get_statement(self, student_id: UUID) -> StudentStatementDTO:
        student = await self.repo.get_with_invoices(student_id)
        if not student:
            raise EntityNotFoundError("Student", student_id)

        # Get financials
        financials = await self.repo.get_student_financials(student_id)

        # Build invoice summaries with payments
        invoice_summaries = []
        for inv in student.invoices:
            if inv.status == InvoiceStatus.CANCELLED:
                continue

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

        school_name = student.school.name if student.school else "Unknown"

        return StudentStatementDTO(
            student_id=student.id,
            student_name=student.full_name,
            school_name=school_name,
            summary=FinancialSummaryDTO(
                total_invoiced=financials["total_invoiced"],
                total_paid=financials["total_paid"],
                total_pending=financials["total_pending"],
                total_overdue=financials["total_overdue"],
            ),
            invoices=invoice_summaries,
            generated_at=datetime.utcnow(),
        )
