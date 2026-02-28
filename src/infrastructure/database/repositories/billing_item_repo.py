from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import BillingItem
from src.infrastructure.database.repositories.base import BaseRepository


class BillingItemRepository(BaseRepository[BillingItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(BillingItem, session)

    async def get_by_school(
        self,
        school_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        recurring_only: bool = None,
    ) -> List[BillingItem]:
        """Get all billing items for a school."""
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        if recurring_only is not None:
            filters["is_recurring"] = recurring_only
        return await self.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_academic_year(
        self,
        school_id: UUID,
        academic_year: str,
        active_only: bool = True,
    ) -> List[BillingItem]:
        """Get billing items for a specific academic year."""
        query = select(BillingItem).where(
            BillingItem.school_id == school_id,
            BillingItem.academic_year == academic_year,
        )
        if active_only:
            query = query.where(BillingItem.is_active == True)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, school_id: UUID, name: str) -> BillingItem | None:
        """Get a billing item by name within a school."""
        query = select(BillingItem).where(
            BillingItem.school_id == school_id,
            BillingItem.name == name,
            BillingItem.is_active == True,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
