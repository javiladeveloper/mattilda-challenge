from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Payment
from src.infrastructure.database.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_invoice(
        self, invoice_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        return await self.get_all(
            skip=skip, limit=limit, filters={"invoice_id": invoice_id}
        )

    async def get_all_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        invoice_id: UUID = None,
        method: str = None,
    ) -> List[Payment]:
        query = select(Payment)

        if invoice_id:
            query = query.where(Payment.invoice_id == invoice_id)
        if method:
            query = query.where(Payment.method == method)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
