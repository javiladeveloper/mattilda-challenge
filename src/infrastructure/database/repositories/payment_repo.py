from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import models as orm
from src.domain.entities.invoice import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_domain(row: orm.Payment) -> Payment:
        return Payment(
            id=row.id,
            invoice_id=row.invoice_id,
            amount=row.amount,
            method=row.method,
            reference=row.reference or "",
            payment_date=row.payment_date,
            created_at=row.created_at,
        )

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        result = await self._session.execute(
            select(orm.Payment).where(orm.Payment.id == payment_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict] = None
    ) -> List[Payment]:
        query = select(orm.Payment)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Payment, key) and value is not None:
                    query = query.where(getattr(orm.Payment, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_invoice(
        self, invoice_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        return await self.get_all(skip=skip, limit=limit, filters={"invoice_id": invoice_id})

    async def count(self, filters: Optional[Dict] = None) -> int:
        query = select(func.count()).select_from(orm.Payment)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Payment, key) and value is not None:
                    query = query.where(getattr(orm.Payment, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one()
