from typing import List, Optional
from uuid import UUID
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database.models import Invoice, Student
from src.infrastructure.database.repositories.base import BaseRepository
from src.domain.enums import InvoiceStatus


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession):
        super().__init__(Invoice, session)

    async def get_by_student(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[InvoiceStatus] = None,
    ) -> List[Invoice]:
        filters = {"student_id": student_id}
        if status:
            filters["status"] = status
        return await self.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_school(
        self,
        school_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[InvoiceStatus] = None,
    ) -> List[Invoice]:
        query = (
            select(Invoice)
            .join(Student, Invoice.student_id == Student.id)
            .where(Student.school_id == school_id)
        )

        if status:
            query = query.where(Invoice.status == status)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_payments(self, invoice_id: UUID) -> Optional[Invoice]:
        query = (
            select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_overdue_invoices(self) -> List[Invoice]:
        today = date.today()
        query = select(Invoice).where(
            and_(
                Invoice.due_date < today,
                Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_overdue_status(self) -> int:
        invoices = await self.get_overdue_invoices()
        count = 0
        for invoice in invoices:
            invoice.status = InvoiceStatus.OVERDUE
            count += 1
        await self.session.flush()
        return count

    async def get_overdue_by_school(self, school_id: UUID, limit: int = 50) -> List[Invoice]:
        """Get overdue invoices for a school with eager-loaded student."""
        today = date.today()
        query = (
            select(Invoice)
            .options(selectinload(Invoice.student))
            .join(Student, Invoice.student_id == Student.id)
            .where(
                and_(
                    Student.school_id == school_id,
                    Invoice.due_date < today,
                    Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]),
                )
            )
            .order_by(Invoice.due_date)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
