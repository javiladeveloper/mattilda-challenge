from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import School, Invoice, Student
from src.infrastructure.database.repositories import SchoolRepository, InvoiceRepository
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus
from src.application.dto.statements import (
    SchoolStatementDTO,
    InvoiceSummaryDTO,
    FinancialSummaryDTO,
    PeriodDTO,
)


class SchoolService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SchoolRepository(session)
        self.invoice_repo = InvoiceRepository(session)

    async def get_all(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[School]:
        if active_only:
            return await self.repo.get_active_schools(skip=skip, limit=limit)
        return await self.repo.get_all(skip=skip, limit=limit)

    async def get_by_id(self, school_id: UUID) -> School:
        school = await self.repo.get_by_id(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)
        return school

    async def create(self, data: dict) -> School:
        return await self.repo.create(data)

    async def update(self, school_id: UUID, data: dict) -> School:
        school = await self.repo.update(school_id, data)
        if not school:
            raise EntityNotFoundError("School", school_id)
        return school

    async def delete(self, school_id: UUID) -> School:
        school = await self.repo.soft_delete(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)
        return school

    async def count(self, active_only: bool = False) -> int:
        filters = {"is_active": True} if active_only else None
        return await self.repo.count(filters)

    async def get_statement(
        self,
        school_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> SchoolStatementDTO:
        school = await self.get_by_id(school_id)

        # Get student counts
        total_students = await self.repo.get_student_count(school_id, active_only=False)
        active_students = await self.repo.get_student_count(school_id, active_only=True)

        # Get financials
        financials = await self.repo.get_school_financials(school_id)

        # Get invoices for this school
        invoices = await self.invoice_repo.get_by_school(school_id, limit=1000)

        invoice_summaries = []
        for inv in invoices:
            if inv.status == InvoiceStatus.CANCELLED:
                continue

            # Apply date filters if provided
            if from_date and inv.created_at.date() < from_date:
                continue
            if to_date and inv.created_at.date() > to_date:
                continue

            student_name = inv.student.full_name if inv.student else None
            invoice_summaries.append(
                InvoiceSummaryDTO(
                    id=inv.id,
                    description=inv.description,
                    amount=inv.amount,
                    paid_amount=inv.paid_amount,
                    pending_amount=inv.pending_amount,
                    status=inv.status,
                    due_date=inv.due_date,
                    student_name=student_name,
                )
            )

        return SchoolStatementDTO(
            school_id=school.id,
            school_name=school.name,
            period=PeriodDTO(from_date=from_date, to_date=to_date),
            summary=FinancialSummaryDTO(
                total_invoiced=financials["total_invoiced"],
                total_paid=financials["total_paid"],
                total_pending=financials["total_pending"],
                total_overdue=financials["total_overdue"],
            ),
            total_students=total_students,
            active_students=active_students,
            invoices=invoice_summaries,
            generated_at=datetime.utcnow(),
        )
