from typing import List
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import Payment
from src.infrastructure.database.repositories import PaymentRepository, InvoiceRepository
from src.domain.exceptions import (
    EntityNotFoundError,
    PaymentExceedsDebtError,
    InvoiceCancelledError,
)
from src.domain.enums import InvoiceStatus, PaymentMethod
from src.application.services.invoice_service import InvoiceService


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PaymentRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.invoice_service = InvoiceService(session)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        invoice_id: UUID = None,
        method: PaymentMethod = None,
    ) -> List[Payment]:
        if invoice_id:
            return await self.repo.get_by_invoice(invoice_id, skip=skip, limit=limit)
        return await self.repo.get_all_with_filters(
            skip=skip, limit=limit, invoice_id=invoice_id, method=method
        )

    async def get_by_id(self, payment_id: UUID) -> Payment:
        payment = await self.repo.get_by_id(payment_id)
        if not payment:
            raise EntityNotFoundError("Payment", payment_id)
        return payment

    async def get_by_invoice(self, invoice_id: UUID) -> List[Payment]:
        # Verify invoice exists
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)
        return await self.repo.get_by_invoice(invoice_id)

    async def create(self, data: dict) -> Payment:
        invoice_id = data.get("invoice_id")

        # Get invoice with payments
        invoice = await self.invoice_repo.get_with_payments(invoice_id)
        if not invoice:
            raise EntityNotFoundError("Invoice", invoice_id)

        # Check if invoice is cancelled
        if invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceCancelledError(invoice_id)

        # Calculate pending amount
        payment_amount = Decimal(str(data.get("amount", 0)))
        pending = invoice.pending_amount

        # Check if payment exceeds pending amount
        if payment_amount > pending:
            raise PaymentExceedsDebtError(float(payment_amount), float(pending))

        # Create payment
        payment = await self.repo.create(data)

        # Refresh invoice to get updated payments
        await self.session.refresh(invoice)

        # Update invoice status
        await self.invoice_service.update_invoice_status(invoice)

        return payment

    async def count(self, invoice_id: UUID = None) -> int:
        filters = {"invoice_id": invoice_id} if invoice_id else None
        return await self.repo.count(filters)
