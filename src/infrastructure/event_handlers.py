from __future__ import annotations

import structlog

from src.domain.events import (
    DomainEvent,
    InvoiceCancelled,
    InvoiceOverdue,
    InvoicePaid,
    PaymentRecorded,
    SchoolDeactivated,
    StudentDeactivated,
)

logger = structlog.get_logger("domain.events")


class AuditLogHandler:
    async def handle(self, event: DomainEvent) -> None:
        event_name = type(event).__name__
        event_data = {
            k: str(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in event.__dict__.items()
            if k != "occurred_at"
        }
        await logger.ainfo(
            "domain_event",
            event_type=event_name,
            occurred_at=event.occurred_at.isoformat(),
            **event_data,
        )


class InvoiceEventHandler:
    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, InvoiceOverdue):
            await logger.awarning(
                "invoice_overdue_alert",
                invoice_id=str(event.invoice_id),
                student_id=str(event.student_id),
                days_overdue=event.days_overdue,
            )
        elif isinstance(event, InvoicePaid):
            await logger.ainfo(
                "invoice_fully_paid",
                invoice_id=str(event.invoice_id),
                student_id=str(event.student_id),
                amount=float(event.amount),
            )
        elif isinstance(event, InvoiceCancelled):
            await logger.ainfo(
                "invoice_cancelled",
                invoice_id=str(event.invoice_id),
                student_id=str(event.student_id),
            )
