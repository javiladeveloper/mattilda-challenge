from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Invoice
from src.infrastructure.database.repositories import InvoiceRepository, StudentRepository
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus


class InvoiceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = InvoiceRepository(session)
        self.student_repo = StudentRepository(session)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        student_id: UUID = None,
        school_id: UUID = None,
        status: InvoiceStatus = None,
    ) -> List[Invoice]:
        if student_id:
            return await self.repo.get_by_student(student_id, skip=skip, limit=limit, status=status)
        if school_id:
            return await self.repo.get_by_school(school_id, skip=skip, limit=limit, status=status)
        filters = {"status": status} if status else None
        return await self.repo.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_id(self, invoice_id: UUID) -> Invoice:
        invoice = await self.repo.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return invoice

    async def create(self, data: dict) -> Invoice:
        # Verify student exists
        student = await self.student_repo.get_by_id(data.get("student_id"))
        if not student:
            raise EntityNotFoundError("Student", data.get("student_id"))

        # Set default status if not provided
        if "status" not in data:
            data["status"] = InvoiceStatus.PENDING

        return await self.repo.create(data)

    async def update(self, invoice_id: UUID, data: dict) -> Invoice:
        invoice = await self.repo.update(invoice_id, data)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return invoice

    async def cancel(self, invoice_id: UUID) -> Invoice:
        invoice = await self.repo.update(invoice_id, {"status": InvoiceStatus.CANCELLED})
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return invoice

    async def count(
        self, student_id: UUID = None, school_id: UUID = None, status: InvoiceStatus = None
    ) -> int:
        filters = {}
        if student_id:
            filters["student_id"] = student_id
        if status:
            filters["status"] = status
        return await self.repo.count(filters if filters else None)

    async def update_overdue_invoices(self) -> int:
        return await self.repo.update_overdue_status()

    async def update_invoice_status(self, invoice: Invoice) -> Invoice:
        if invoice.status == InvoiceStatus.CANCELLED:
            return invoice

        paid = invoice.paid_amount
        total = invoice.amount

        if paid >= total:
            invoice.status = InvoiceStatus.PAID
        elif paid > 0:
            invoice.status = InvoiceStatus.PARTIAL
        else:
            invoice.status = InvoiceStatus.PENDING

        await self.session.flush()
        return invoice
