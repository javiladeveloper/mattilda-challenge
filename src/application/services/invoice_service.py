from typing import List
from uuid import UUID

from src.domain.entities.invoice import Invoice
from src.domain.interfaces.unit_of_work import UnitOfWork
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus


class InvoiceService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        student_id: UUID = None,
        school_id: UUID = None,
        status: InvoiceStatus = None,
    ) -> List[Invoice]:
        if student_id:
            return await self._uow.invoices.get_by_student(
                student_id, skip=skip, limit=limit, status=status
            )
        if school_id:
            return await self._uow.invoices.get_by_school(
                school_id, skip=skip, limit=limit, status=status
            )
        filters = {"status": status} if status else None
        return await self._uow.invoices.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_id(self, invoice_id: UUID) -> Invoice:
        invoice = await self._uow.invoices.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return invoice

    async def create(self, data: dict) -> Invoice:
        student = await self._uow.students.get_by_id(data.get("student_id"))
        if not student:
            raise EntityNotFoundError("Student", data.get("student_id"))

        invoice = Invoice(
            student_id=data["student_id"],
            amount=data["amount"],
            due_date=data["due_date"],
            description=data.get("description", ""),
        )
        saved = await self._uow.invoices.save(invoice)
        self._uow.track(invoice)
        await self._uow.commit()
        return saved

    async def update(self, invoice_id: UUID, data: dict) -> Invoice:
        invoice = await self._uow.invoices.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)

        invoice.update_details(
            amount=data.get("amount"),
            due_date=data.get("due_date"),
            description=data.get("description"),
        )

        saved = await self._uow.invoices.save(invoice)
        self._uow.track(invoice)
        await self._uow.commit()
        return saved

    async def cancel(self, invoice_id: UUID) -> Invoice:
        invoice = await self._uow.invoices.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        invoice.cancel()
        saved = await self._uow.invoices.save(invoice)
        self._uow.track(invoice)
        await self._uow.commit()
        return saved

    async def count(
        self, student_id: UUID = None, school_id: UUID = None, status: InvoiceStatus = None
    ) -> int:
        filters = {}
        if student_id:
            filters["student_id"] = student_id
        if school_id:
            filters["school_id"] = school_id
        if status:
            filters["status"] = status
        return await self._uow.invoices.count(filters if filters else None)

    async def update_overdue_invoices(self) -> int:
        return await self._uow.invoices.update_overdue_status()

    async def get_overdue_by_school(self, school_id: UUID, limit: int = 50) -> list[dict]:
        return await self._uow.invoices.get_overdue_by_school(school_id, limit=limit)
