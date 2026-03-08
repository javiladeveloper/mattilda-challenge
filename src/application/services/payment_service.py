from typing import List
from uuid import UUID

from src.domain.entities.invoice import Payment
from src.domain.interfaces.unit_of_work import UnitOfWork
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import PaymentMethod


class PaymentService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        invoice_id: UUID = None,
        method: PaymentMethod = None,
    ) -> List[Payment]:
        if invoice_id:
            return await self._uow.payments.get_by_invoice(invoice_id, skip=skip, limit=limit)
        filters = {}
        if method:
            filters["method"] = method
        return await self._uow.payments.get_all(skip=skip, limit=limit, filters=filters or None)

    async def get_by_id(self, payment_id: UUID) -> Payment:
        payment = await self._uow.payments.get_by_id(payment_id)
        if not payment:
            raise EntityNotFoundError("Payment", payment_id)
        return payment

    async def get_by_invoice(self, invoice_id: UUID) -> List[Payment]:
        invoice = await self._uow.invoices.get_by_id(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return await self._uow.payments.get_by_invoice(invoice_id)

    async def create(self, data: dict) -> Payment:
        invoice_id = data.get("invoice_id")

        invoice = await self._uow.invoices.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)

        payment = invoice.record_payment(
            amount=data["amount"],
            method=data.get("method", PaymentMethod.CASH),
            reference=data.get("reference", ""),
            payment_date=data.get("payment_date"),
        )

        await self._uow.invoices.save(invoice)
        self._uow.track(invoice)
        await self._uow.commit()

        return payment

    async def count(self, invoice_id: UUID = None) -> int:
        filters = {"invoice_id": invoice_id} if invoice_id else None
        return await self._uow.payments.count(filters)
