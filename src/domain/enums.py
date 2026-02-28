from enum import Enum


class InvoiceStatus(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    OTHER = "OTHER"


class InvoiceType(str, Enum):
    """Type of invoice based on what it charges for."""
    TUITION = "TUITION"          # Monthly tuition from grade
    ENROLLMENT = "ENROLLMENT"    # Enrollment/matricula fee
    FEE = "FEE"                  # Other billing items (food, transport, etc.)
    CUSTOM = "CUSTOM"            # Manual entry with custom amount
