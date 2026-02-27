from typing import List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models import Student, Invoice
from src.infrastructure.database.repositories.base import BaseRepository
from src.domain.enums import InvoiceStatus


class StudentRepository(BaseRepository[Student]):
    def __init__(self, session: AsyncSession):
        super().__init__(Student, session)

    async def get_by_school(
        self, school_id: UUID, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[Student]:
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        return await self.get_all(skip=skip, limit=limit, filters=filters)

    async def get_with_invoices(self, student_id: UUID) -> Student | None:
        query = (
            select(Student)
            .options(
                selectinload(Student.school),
                selectinload(Student.invoices).selectinload(Invoice.payments),
            )
            .where(Student.id == student_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_student_financials(self, student_id: UUID) -> dict:
        query = (
            select(Invoice)
            .options(selectinload(Invoice.payments))
            .where(Invoice.student_id == student_id)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        result = await self.session.execute(query)
        invoices = result.scalars().all()

        total_invoiced = Decimal("0")
        total_paid = Decimal("0")
        total_pending = Decimal("0")
        total_overdue = Decimal("0")

        for invoice in invoices:
            total_invoiced += invoice.amount
            paid = invoice.paid_amount
            pending = invoice.pending_amount
            total_paid += paid

            if invoice.status == InvoiceStatus.OVERDUE:
                total_overdue += pending
            elif invoice.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]:
                total_pending += pending

        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_pending": total_pending,
            "total_overdue": total_overdue,
        }
