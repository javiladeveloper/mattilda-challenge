from src.infrastructure.database.repositories.base import BaseRepository
from src.infrastructure.database.repositories.school_repo import SchoolRepository
from src.infrastructure.database.repositories.student_repo import StudentRepository
from src.infrastructure.database.repositories.invoice_repo import InvoiceRepository
from src.infrastructure.database.repositories.payment_repo import PaymentRepository

__all__ = [
    "BaseRepository",
    "SchoolRepository",
    "StudentRepository",
    "InvoiceRepository",
    "PaymentRepository",
]
