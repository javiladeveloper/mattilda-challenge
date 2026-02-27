from typing import Any


class DomainException(Exception):
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class EntityNotFoundError(DomainException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found",
            details={"entity": entity_name, "id": str(entity_id)},
        )


class ValidationError(DomainException):
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            details={"field": field} if field else None,
        )


class BusinessRuleError(DomainException):
    def __init__(self, message: str, rule: str = None):
        super().__init__(
            message=message,
            details={"rule": rule} if rule else None,
        )


class PaymentExceedsDebtError(BusinessRuleError):
    def __init__(self, payment_amount: float, pending_amount: float):
        super().__init__(
            message=f"Payment amount ({payment_amount}) exceeds pending amount ({pending_amount})",
            rule="payment_cannot_exceed_debt",
        )


class InvoiceCancelledError(BusinessRuleError):
    def __init__(self, invoice_id: Any):
        super().__init__(
            message=f"Cannot process payment for cancelled invoice '{invoice_id}'",
            rule="no_payment_for_cancelled_invoice",
        )
