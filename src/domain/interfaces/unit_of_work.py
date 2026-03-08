from typing import Protocol

from src.domain.interfaces.repositories import (
    SchoolRepository,
    StudentRepository,
    InvoiceRepository,
    PaymentRepository,
)


class UnitOfWork(Protocol):
    schools: SchoolRepository
    students: StudentRepository
    invoices: InvoiceRepository
    payments: PaymentRepository

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def track(self, aggregate) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
