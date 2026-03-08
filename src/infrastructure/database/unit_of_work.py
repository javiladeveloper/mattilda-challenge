from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.events import DomainEvent
from src.domain.event_dispatcher import DomainEventDispatcher
from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.repositories.school_repo import SchoolRepository
from src.infrastructure.database.repositories.student_repo import StudentRepository
from src.infrastructure.database.repositories.invoice_repo import InvoiceRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory=None,
        event_dispatcher: DomainEventDispatcher | None = None,
    ) -> None:
        self._session_factory = session_factory or AsyncSessionLocal
        self._event_dispatcher = event_dispatcher
        self._seen: list = []

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session: AsyncSession = self._session_factory()
        self.schools = SchoolRepository(self._session)
        self.students = StudentRepository(self._session)
        self.invoices = InvoiceRepository(self._session)
        self.payments = PaymentRepository(self._session)
        self._seen = []
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type:
                await self.rollback()
        finally:
            await self._session.close()

    def track(self, aggregate) -> None:
        if aggregate not in self._seen:
            self._seen.append(aggregate)

    async def commit(self) -> None:
        await self._session.commit()
        await self._dispatch_events()

    async def rollback(self) -> None:
        await self._session.rollback()
        self._seen.clear()

    async def _dispatch_events(self) -> None:
        if not self._event_dispatcher:
            return

        events: List[DomainEvent] = []
        for aggregate in self._seen:
            if hasattr(aggregate, "domain_events"):
                events.extend(aggregate.domain_events)
            if hasattr(aggregate, "clear_events"):
                aggregate.clear_events()

        self._seen.clear()

        if events:
            await self._event_dispatcher.dispatch(events)
