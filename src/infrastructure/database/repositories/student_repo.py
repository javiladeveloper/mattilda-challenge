from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import models as orm
from src.domain.entities.student import Student


class StudentRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _to_domain(row: orm.Student) -> Student:
        return Student(
            id=row.id,
            first_name=row.first_name,
            last_name=row.last_name,
            school_id=row.school_id,
            email=row.email,
            grade=row.grade or "",
            is_active=row.is_active,
            enrolled_at=row.enrolled_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_id(self, student_id: UUID) -> Optional[Student]:
        result = await self._session.execute(
            select(orm.Student).where(orm.Student.id == student_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict] = None
    ) -> List[Student]:
        query = select(orm.Student)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Student, key) and value is not None:
                    query = query.where(getattr(orm.Student, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def get_by_school(
        self, school_id: UUID, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[Student]:
        filters = {"school_id": school_id}
        if active_only:
            filters["is_active"] = True
        return await self.get_all(skip=skip, limit=limit, filters=filters)

    async def save(self, entity: Student) -> Student:
        existing = await self._session.get(orm.Student, entity.id)
        if existing:
            existing.first_name = entity.first_name
            existing.last_name = entity.last_name
            existing.school_id = entity.school_id
            existing.email = entity.email
            existing.grade = entity.grade
            existing.is_active = entity.is_active
        else:
            existing = orm.Student(
                id=entity.id,
                first_name=entity.first_name,
                last_name=entity.last_name,
                school_id=entity.school_id,
                email=entity.email,
                grade=entity.grade,
                is_active=entity.is_active,
                enrolled_at=entity.enrolled_at,
            )
            self._session.add(existing)
        await self._session.flush()
        await self._session.refresh(existing)
        return self._to_domain(existing)

    async def count(self, filters: Optional[Dict] = None) -> int:
        query = select(func.count()).select_from(orm.Student)
        if filters:
            for key, value in filters.items():
                if hasattr(orm.Student, key) and value is not None:
                    query = query.where(getattr(orm.Student, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one()
