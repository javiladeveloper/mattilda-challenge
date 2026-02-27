from typing import Generic, TypeVar, Type, Optional, List, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] = None,
    ) -> List[ModelType]:
        query = select(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] = None) -> int:
        query = select(func.count()).select_from(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, obj_data: dict) -> ModelType:
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, id: UUID, obj_data: dict) -> Optional[ModelType]:
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None

        for key, value in obj_data.items():
            if hasattr(db_obj, key) and value is not None:
                setattr(db_obj, key, value)

        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: UUID) -> bool:
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def soft_delete(self, id: UUID) -> Optional[ModelType]:
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None

        if hasattr(db_obj, "is_active"):
            db_obj.is_active = False
            await self.session.flush()
            await self.session.refresh(db_obj)
            return db_obj

        return None
