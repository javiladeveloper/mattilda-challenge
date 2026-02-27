from typing import List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import School, Student, Invoice
from src.infrastructure.database.repositories.base import BaseRepository
from src.domain.enums import InvoiceStatus


class SchoolRepository(BaseRepository[School]):
    def __init__(self, session: AsyncSession):
        super().__init__(School, session)

    async def get_active_schools(self, skip: int = 0, limit: int = 100) -> List[School]:
        return await self.get_all(skip=skip, limit=limit, filters={"is_active": True})

    async def get_student_count(self, school_id: UUID, active_only: bool = True) -> int:
        query = select(func.count()).select_from(Student).where(Student.school_id == school_id)
        if active_only:
            query = query.where(Student.is_active.is_(True))

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_school_financials(self, school_id: UUID) -> dict:
        # Total invoiced
        total_invoiced_query = (
            select(func.coalesce(func.sum(Invoice.amount), 0))
            .select_from(Invoice)
            .join(Student, Invoice.student_id == Student.id)
            .where(Student.school_id == school_id)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        total_invoiced = await self.session.execute(total_invoiced_query)

        # Invoices by status for this school
        invoices_query = (
            select(Invoice)
            .join(Student, Invoice.student_id == Student.id)
            .where(Student.school_id == school_id)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
        invoices_result = await self.session.execute(invoices_query)
        invoices = invoices_result.scalars().all()

        total_paid = Decimal("0")
        total_pending = Decimal("0")
        total_overdue = Decimal("0")

        for invoice in invoices:
            paid = invoice.paid_amount
            pending = invoice.pending_amount
            total_paid += paid

            if invoice.status == InvoiceStatus.OVERDUE:
                total_overdue += pending
            elif invoice.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]:
                total_pending += pending

        return {
            "total_invoiced": total_invoiced.scalar_one(),
            "total_paid": total_paid,
            "total_pending": total_pending,
            "total_overdue": total_overdue,
        }
