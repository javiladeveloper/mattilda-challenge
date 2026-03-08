from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import models as orm
from src.domain.entities.school import School
from src.domain.enums import InvoiceStatus


class SchoolRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_domain(row: orm.School) -> School:
        return School(
            id=row.id,
            name=row.name,
            address=row.address or "",
            phone=row.phone or "",
            email=row.email,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_id(self, school_id: UUID) -> Optional[School]:
        result = await self._session.execute(
            select(orm.School).where(orm.School.id == school_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict] = None
    ) -> List[School]:
        query = select(orm.School)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.School, key) and value is not None:
                    query = query.where(getattr(orm.School, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def save(self, entity: School) -> School:
        existing = await self._session.get(orm.School, entity.id)
        if existing:
            existing.name = entity.name
            existing.address = entity.address
            existing.phone = entity.phone
            existing.email = entity.email
            existing.is_active = entity.is_active
        else:
            existing = orm.School(
                id=entity.id,
                name=entity.name,
                address=entity.address,
                phone=entity.phone,
                email=entity.email,
                is_active=entity.is_active,
            )
            self._session.add(existing)
        await self._session.flush()
        await self._session.refresh(existing)
        return self._to_domain(existing)

    async def count(self, filters: Optional[Dict] = None) -> int:
        query = select(func.count()).select_from(orm.School)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.School, key) and value is not None:
                    query = query.where(getattr(orm.School, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_student_count(self, school_id: UUID, active_only: bool = True) -> int:
        query = select(func.count()).select_from(orm.Student).where(
            orm.Student.school_id == school_id
        )
        if active_only:
            query = query.where(orm.Student.is_active.is_(True))
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_school_financials(self, school_id: UUID) -> dict:
        total_invoiced_query = (
            select(func.coalesce(func.sum(orm.Invoice.amount), 0))
            .select_from(orm.Invoice)
            .join(orm.Student, orm.Invoice.student_id == orm.Student.id)
            .where(orm.Student.school_id == school_id)
            .where(orm.Invoice.status != InvoiceStatus.CANCELLED)
        )
        total_invoiced = await self._session.execute(total_invoiced_query)

        invoices_query = (
            select(orm.Invoice)
            .join(orm.Student, orm.Invoice.student_id == orm.Student.id)
            .where(orm.Student.school_id == school_id)
            .where(orm.Invoice.status != InvoiceStatus.CANCELLED)
        )
        invoices_result = await self._session.execute(invoices_query)
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
