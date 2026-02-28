from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import BillingItem
from src.infrastructure.database.repositories import BillingItemRepository, SchoolRepository
from src.domain.exceptions import EntityNotFoundError


class BillingItemService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BillingItemRepository(session)
        self.school_repo = SchoolRepository(session)

    async def get_all(
        self,
        school_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        recurring_only: bool = None,
    ) -> List[BillingItem]:
        """Get all billing items for a school."""
        return await self.repo.get_by_school(
            school_id,
            skip=skip,
            limit=limit,
            active_only=active_only,
            recurring_only=recurring_only,
        )

    async def get_by_id(self, item_id: UUID) -> BillingItem:
        """Get a billing item by ID."""
        item = await self.repo.get_by_id(item_id)
        if not item:
            raise EntityNotFoundError("BillingItem", item_id)
        return item

    async def get_by_academic_year(
        self,
        school_id: UUID,
        academic_year: str,
        active_only: bool = True,
    ) -> List[BillingItem]:
        """Get billing items for a specific academic year."""
        return await self.repo.get_by_academic_year(school_id, academic_year, active_only)

    async def create(self, data: dict) -> BillingItem:
        """Create a new billing item."""
        # Verify school exists
        school = await self.school_repo.get_by_id(data.get("school_id"))
        if not school:
            raise EntityNotFoundError("School", data.get("school_id"))

        return await self.repo.create(data)

    async def update(self, item_id: UUID, data: dict) -> BillingItem:
        """Update a billing item."""
        item = await self.repo.update(item_id, data)
        if not item:
            raise EntityNotFoundError("BillingItem", item_id)
        return item

    async def delete(self, item_id: UUID) -> BillingItem:
        """Soft delete a billing item."""
        item = await self.repo.soft_delete(item_id)
        if not item:
            raise EntityNotFoundError("BillingItem", item_id)
        return item

    async def count(
        self,
        school_id: UUID,
        active_only: bool = True,
        recurring_only: bool = None,
    ) -> int:
        """Count billing items for a school."""
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        if recurring_only is not None:
            filters["is_recurring"] = recurring_only
        return await self.repo.count(filters)
