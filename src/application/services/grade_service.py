from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Grade
from src.infrastructure.database.repositories import GradeRepository, SchoolRepository
from src.domain.exceptions import EntityNotFoundError


class GradeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GradeRepository(session)
        self.school_repo = SchoolRepository(session)

    async def get_all(
        self,
        school_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Grade]:
        """Get all grades for a school."""
        return await self.repo.get_by_school(
            school_id, skip=skip, limit=limit, active_only=active_only
        )

    async def get_by_id(self, grade_id: UUID) -> Grade:
        """Get a grade by ID."""
        grade = await self.repo.get_by_id(grade_id)
        if not grade:
            raise EntityNotFoundError("Grade", grade_id)
        return grade

    async def create(self, data: dict) -> Grade:
        """Create a new grade."""
        # Verify school exists
        school = await self.school_repo.get_by_id(data.get("school_id"))
        if not school:
            raise EntityNotFoundError("School", data.get("school_id"))

        return await self.repo.create(data)

    async def update(self, grade_id: UUID, data: dict) -> Grade:
        """Update a grade."""
        grade = await self.repo.update(grade_id, data)
        if not grade:
            raise EntityNotFoundError("Grade", grade_id)
        return grade

    async def delete(self, grade_id: UUID) -> Grade:
        """Soft delete a grade."""
        grade = await self.repo.soft_delete(grade_id)
        if not grade:
            raise EntityNotFoundError("Grade", grade_id)
        return grade

    async def count(self, school_id: UUID, active_only: bool = True) -> int:
        """Count grades for a school."""
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        return await self.repo.count(filters)
