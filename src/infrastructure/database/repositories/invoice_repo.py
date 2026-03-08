from typing import Dict, List, Optional
from uuid import UUID
from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infrastructure.database import models as orm
from src.domain.entities.invoice import Invoice, Payment
from src.domain.enums import InvoiceStatus


class InvoiceRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_domain(row: orm.Invoice) -> Invoice:
        payments = []
        if row.payments:
            payments = [
                Payment(
                    id=p.id,
                    invoice_id=p.invoice_id,
                    amount=p.amount,
                    method=p.method,
                    reference=p.reference or "",
                    payment_date=p.payment_date,
                    created_at=p.created_at,
                )
                for p in row.payments
            ]
        return Invoice(
            id=row.id,
            student_id=row.student_id,
            amount=row.amount,
            due_date=row.due_date,
            description=row.description or "",
            status=row.status,
            payments=payments,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _base_query(self):
        return select(orm.Invoice).options(selectinload(orm.Invoice.payments))

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        return await self.get_with_payments(invoice_id)

    async def get_with_payments(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self._session.execute(
            self._base_query().where(orm.Invoice.id == invoice_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict] = None
    ) -> List[Invoice]:
        query = self._base_query()
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Invoice, key) and value is not None:
                    query = query.where(getattr(orm.Invoice, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_student(
        self, student_id: UUID, skip: int = 0, limit: int = 100,
        status: Optional[InvoiceStatus] = None,
    ) -> List[Invoice]:
        query = self._base_query().where(orm.Invoice.student_id == student_id)
        if status:
            query = query.where(orm.Invoice.status == status)
        query = query.order_by(orm.Invoice.due_date.desc()).offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_school(
        self, school_id: UUID, skip: int = 0, limit: int = 100,
        status: Optional[InvoiceStatus] = None,
    ) -> List[Invoice]:
        query = (
            self._base_query()
            .join(orm.Student, orm.Invoice.student_id == orm.Student.id)
            .where(orm.Student.school_id == school_id)
        )
        if status:
            query = query.where(orm.Invoice.status == status)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def save(self, entity: Invoice) -> Invoice:
        existing = await self._session.get(orm.Invoice, entity.id)
        if existing:
            existing.amount = entity.amount
            existing.due_date = entity.due_date
            existing.description = entity.description
            existing.status = entity.status
        else:
            existing = orm.Invoice(
                id=entity.id,
                student_id=entity.student_id,
                amount=entity.amount,
                due_date=entity.due_date,
                description=entity.description,
                status=entity.status,
            )
            self._session.add(existing)

        await self._save_new_payments(entity)
        await self._session.flush()
        return await self.get_with_payments(entity.id)

    async def _save_new_payments(self, entity: Invoice) -> None:
        result = await self._session.execute(
            select(orm.Payment.id).where(orm.Payment.invoice_id == entity.id)
        )
        existing_ids = {row[0] for row in result.all()}

        for payment in entity.payments:
            if payment.id not in existing_ids:
                self._session.add(orm.Payment(
                    id=payment.id,
                    invoice_id=payment.invoice_id,
                    amount=payment.amount,
                    method=payment.method,
                    reference=payment.reference,
                    payment_date=payment.payment_date,
                ))

    async def count(self, filters: Optional[Dict] = None) -> int:
        query = select(func.count()).select_from(orm.Invoice)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Invoice, key) and value is not None:
                    query = query.where(getattr(orm.Invoice, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_by_school_with_details(self, school_id: UUID, limit: int = 1000) -> list[dict]:
        query = (
            select(orm.Invoice)
            .options(
                selectinload(orm.Invoice.payments),
                selectinload(orm.Invoice.student),
            )
            .join(orm.Student)
            .where(orm.Student.school_id == school_id)
            .where(orm.Invoice.status != InvoiceStatus.CANCELLED)
            .limit(limit)
        )
        result = await self._session.execute(query)
        invoices = result.scalars().all()

        return [
            {
                "id": inv.id,
                "description": inv.description,
                "amount": inv.amount,
                "paid_amount": inv.paid_amount,
                "pending_amount": inv.pending_amount,
                "status": inv.status,
                "due_date": inv.due_date,
                "student_name": inv.student.full_name if inv.student else None,
                "created_at": inv.created_at,
            }
            for inv in invoices
        ]

    async def get_overdue_invoices(self) -> List[Invoice]:
        today = date.today()
        query = self._base_query().where(
            and_(
                orm.Invoice.due_date < today,
                orm.Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]),
            )
        )
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def update_overdue_status(self) -> int:
        invoices = await self.get_overdue_invoices()
        count = 0
        for invoice in invoices:
            invoice.mark_overdue()
            await self.save(invoice)
            count += 1
        return count

    async def get_overdue_by_school(self, school_id: UUID, limit: int = 50) -> list[dict]:
        today = date.today()
        query = (
            select(orm.Invoice)
            .options(selectinload(orm.Invoice.student), selectinload(orm.Invoice.payments))
            .join(orm.Student, orm.Invoice.student_id == orm.Student.id)
            .where(
                and_(
                    orm.Student.school_id == school_id,
                    orm.Invoice.due_date < today,
                    orm.Invoice.status.in_(
                        [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]
                    ),
                )
            )
            .order_by(orm.Invoice.due_date)
            .limit(limit)
        )
        result = await self._session.execute(query)
        invoices = result.scalars().all()

        return [
            {
                "id": inv.id,
                "description": inv.description,
                "amount": inv.amount,
                "paid_amount": inv.paid_amount,
                "pending_amount": inv.pending_amount,
                "status": inv.status,
                "due_date": inv.due_date,
                "student_name": inv.student.full_name if inv.student else None,
            }
            for inv in invoices
        ]
