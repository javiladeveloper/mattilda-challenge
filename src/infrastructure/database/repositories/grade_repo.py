from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Grade
from src.infrastructure.database.repositories.base import BaseRepository


class GradeRepository(BaseRepository[Grade]):
    def __init__(self, session: AsyncSession):
        super().__init__(Grade, session)

    async def get_by_school(
        self,
        school_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Grade]:
        """Get all grades for a school."""
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        return await self.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_name(self, school_id: UUID, name: str) -> Grade | None:
        """Get a grade by name within a school."""
        query = select(Grade).where(
            Grade.school_id == school_id,
            Grade.name == name,
            Grade.is_active == True,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
