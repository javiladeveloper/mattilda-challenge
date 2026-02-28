from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.application.services import (
    SchoolService,
    StudentService,
    InvoiceService,
    PaymentService,
    GradeService,
    BillingItemService,
)


async def get_school_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[SchoolService, None]:
    yield SchoolService(db)


async def get_student_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[StudentService, None]:
    yield StudentService(db)


async def get_invoice_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[InvoiceService, None]:
    yield InvoiceService(db)


async def get_payment_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[PaymentService, None]:
    yield PaymentService(db)


async def get_grade_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[GradeService, None]:
    yield GradeService(db)


async def get_billing_item_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[BillingItemService, None]:
    yield BillingItemService(db)
