from typing import AsyncGenerator

from fastapi import Depends

from src.domain.event_dispatcher import DomainEventDispatcher
from src.domain.events import DomainEvent, InvoicePaid, InvoiceCancelled, InvoiceOverdue
from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.infrastructure.event_handlers import AuditLogHandler, InvoiceEventHandler
from src.application.services import (
    SchoolService,
    StudentService,
    InvoiceService,
    PaymentService,
)


def _create_event_dispatcher() -> DomainEventDispatcher:
    dispatcher = DomainEventDispatcher()
    dispatcher.register(DomainEvent, AuditLogHandler())
    invoice_handler = InvoiceEventHandler()
    dispatcher.register(InvoiceOverdue, invoice_handler)
    dispatcher.register(InvoicePaid, invoice_handler)
    dispatcher.register(InvoiceCancelled, invoice_handler)
    return dispatcher


_dispatcher = _create_event_dispatcher()


async def get_unit_of_work() -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    uow = SqlAlchemyUnitOfWork(event_dispatcher=_dispatcher)
    async with uow:
        yield uow


async def get_school_service(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> SchoolService:
    return SchoolService(uow)


async def get_student_service(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> StudentService:
    return StudentService(uow)


async def get_invoice_service(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> InvoiceService:
    return InvoiceService(uow)


async def get_payment_service(
    uow: SqlAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> PaymentService:
    return PaymentService(uow)
