"""Reports API endpoints - Exposes database views for analytics."""

from typing import List, Optional
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import table, column, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData

router = APIRouter(prefix="/reports", tags=["Reports"])


# ============================================
# View table definitions (SQLAlchemy Core)
# ============================================

v_student_balance = table(
    "v_student_balance",
    column("student_id"),
    column("first_name"),
    column("last_name"),
    column("full_name"),
    column("email"),
    column("grade"),
    column("is_active"),
    column("school_id"),
    column("school_name"),
    column("total_invoices"),
    column("total_invoiced"),
    column("total_paid"),
    column("balance_due"),
    column("overdue_invoices"),
    column("pending_invoices"),
    column("partial_invoices"),
    column("paid_invoices"),
)

v_school_summary = table(
    "v_school_summary",
    column("school_id"),
    column("school_name"),
    column("school_email"),
    column("school_phone"),
    column("is_active"),
    column("total_students"),
    column("active_students"),
    column("total_invoices"),
    column("total_invoiced"),
    column("total_collected"),
    column("total_pending"),
    column("total_overdue"),
    column("overdue_invoice_count"),
    column("pending_invoice_count"),
    column("paid_invoice_count"),
)

v_invoice_details = table(
    "v_invoice_details",
    column("invoice_id"),
    column("description"),
    column("invoice_amount"),
    column("due_date"),
    column("status"),
    column("invoice_created_at"),
    column("student_id"),
    column("student_name"),
    column("student_email"),
    column("grade"),
    column("school_id"),
    column("school_name"),
    column("paid_amount"),
    column("pending_amount"),
    column("payment_count"),
    column("last_payment_date"),
    column("days_overdue"),
)

v_payment_history = table(
    "v_payment_history",
    column("payment_id"),
    column("payment_amount"),
    column("payment_date"),
    column("payment_method"),
    column("reference"),
    column("payment_created_at"),
    column("invoice_id"),
    column("invoice_description"),
    column("invoice_amount"),
    column("invoice_status"),
    column("due_date"),
    column("student_id"),
    column("student_name"),
    column("student_email"),
    column("school_id"),
    column("school_name"),
)

v_overdue_invoices = table(
    "v_overdue_invoices",
    column("invoice_id"),
    column("description"),
    column("invoice_amount"),
    column("due_date"),
    column("days_overdue"),
    column("paid_amount"),
    column("pending_amount"),
    column("student_id"),
    column("student_name"),
    column("student_email"),
    column("grade"),
    column("school_id"),
    column("school_name"),
    column("school_phone"),
)

v_daily_collections = table(
    "v_daily_collections",
    column("payment_date"),
    column("school_id"),
    column("school_name"),
    column("payment_count"),
    column("total_collected"),
    column("cash_amount"),
    column("transfer_amount"),
    column("credit_card_amount"),
    column("debit_card_amount"),
    column("other_amount"),
)

v_monthly_revenue = table(
    "v_monthly_revenue",
    column("month"),
    column("school_id"),
    column("school_name"),
    column("students_with_payments"),
    column("payment_count"),
    column("total_revenue"),
    column("avg_payment_amount"),
    column("min_payment"),
    column("max_payment"),
)


# ============================================
# Response Schemas
# ============================================


class StudentBalanceResponse(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    grade: Optional[str]
    is_active: bool
    school_id: str
    school_name: str
    total_invoices: int
    total_invoiced: float
    total_paid: float
    balance_due: float
    overdue_invoices: int
    pending_invoices: int
    partial_invoices: int
    paid_invoices: int

    class Config:
        from_attributes = True


class SchoolSummaryResponse(BaseModel):
    school_id: str
    school_name: str
    school_email: Optional[str]
    school_phone: Optional[str]
    is_active: bool
    total_students: int
    active_students: int
    total_invoices: int
    total_invoiced: float
    total_collected: float
    total_pending: float
    total_overdue: float
    overdue_invoice_count: int
    pending_invoice_count: int
    paid_invoice_count: int

    class Config:
        from_attributes = True


class InvoiceDetailResponse(BaseModel):
    invoice_id: str
    description: Optional[str]
    invoice_amount: float
    due_date: date
    status: str
    student_id: str
    student_name: str
    student_email: Optional[str]
    grade: Optional[str]
    school_id: str
    school_name: str
    paid_amount: float
    pending_amount: float
    payment_count: Optional[int]
    last_payment_date: Optional[date]
    days_overdue: int

    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    payment_id: str
    payment_amount: float
    payment_date: date
    payment_method: str
    reference: Optional[str]
    invoice_id: str
    invoice_description: Optional[str]
    invoice_amount: float
    invoice_status: str
    due_date: date
    student_id: str
    student_name: str
    student_email: Optional[str]
    school_id: str
    school_name: str

    class Config:
        from_attributes = True


class OverdueInvoiceResponse(BaseModel):
    invoice_id: str
    description: Optional[str]
    invoice_amount: float
    due_date: date
    days_overdue: int
    paid_amount: float
    pending_amount: float
    student_id: str
    student_name: str
    student_email: Optional[str]
    grade: Optional[str]
    school_id: str
    school_name: str
    school_phone: Optional[str]

    class Config:
        from_attributes = True


class DailyCollectionResponse(BaseModel):
    payment_date: date
    school_id: str
    school_name: str
    payment_count: int
    total_collected: float
    cash_amount: Optional[float]
    transfer_amount: Optional[float]
    credit_card_amount: Optional[float]
    debit_card_amount: Optional[float]
    other_amount: Optional[float]

    class Config:
        from_attributes = True


class MonthlyRevenueResponse(BaseModel):
    month: date
    school_id: str
    school_name: str
    students_with_payments: int
    payment_count: int
    total_revenue: float
    avg_payment_amount: float
    min_payment: float
    max_payment: float

    class Config:
        from_attributes = True


def _row_to_dict(row) -> dict:
    """Convert a database row mapping to a dict with UUID→str conversion."""
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


# ============================================
# Endpoints
# ============================================


@router.get(
    "/students/balance",
    response_model=List[StudentBalanceResponse],
    summary="Get student balances",
    description="Returns balance summary for all students including total invoiced, paid, and pending amounts.",
)
async def get_student_balances(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    only_with_debt: bool = Query(False, description="Only show students with balance > 0"),
    only_active: bool = Query(True, description="Only show active students"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_student_balance
    query = select(v)

    conditions = []
    if school_id:
        conditions.append(v.c.school_id == str(school_id))
    if only_with_debt:
        conditions.append(v.c.balance_due > 0)
    if only_active:
        conditions.append(v.c.is_active == True)  # noqa: E712

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(v.c.balance_due.desc())

    result = await db.execute(query)
    rows = result.mappings().all()
    return [StudentBalanceResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/schools/summary",
    response_model=List[SchoolSummaryResponse],
    summary="Get school summaries",
    description="Returns financial summary for all schools including totals and invoice counts.",
)
async def get_school_summaries(
    only_active: bool = Query(True, description="Only show active schools"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_school_summary
    query = select(v)

    if only_active:
        query = query.where(v.c.is_active == True)  # noqa: E712

    query = query.order_by(v.c.school_name)

    result = await db.execute(query)
    rows = result.mappings().all()
    return [SchoolSummaryResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/invoices/details",
    response_model=List[InvoiceDetailResponse],
    summary="Get invoice details",
    description="Returns detailed information for all invoices including payment status.",
)
async def get_invoice_details(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    student_id: Optional[UUID] = Query(None, description="Filter by student ID"),
    invoice_status: Optional[str] = Query(
        None, description="Filter by status (PENDING, PARTIAL, PAID, OVERDUE, CANCELLED)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_invoice_details
    query = select(v)

    conditions = []
    if school_id:
        conditions.append(v.c.school_id == str(school_id))
    if student_id:
        conditions.append(v.c.student_id == str(student_id))
    if invoice_status:
        conditions.append(v.c.status == invoice_status)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(v.c.due_date.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.mappings().all()
    return [InvoiceDetailResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/payments/history",
    response_model=List[PaymentHistoryResponse],
    summary="Get payment history",
    description="Returns complete payment history with all related details.",
)
async def get_payment_history(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    student_id: Optional[UUID] = Query(None, description="Filter by student ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_payment_history
    query = select(v)

    conditions = []
    if school_id:
        conditions.append(v.c.school_id == str(school_id))
    if student_id:
        conditions.append(v.c.student_id == str(student_id))
    if date_from:
        conditions.append(v.c.payment_date >= date_from)
    if date_to:
        conditions.append(v.c.payment_date <= date_to)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(v.c.payment_created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.mappings().all()
    return [PaymentHistoryResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/invoices/overdue",
    response_model=List[OverdueInvoiceResponse],
    summary="Get overdue invoices",
    description="Returns all overdue invoices for collections follow-up.",
)
async def get_overdue_invoices(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    min_days_overdue: int = Query(0, ge=0, description="Minimum days overdue"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_overdue_invoices
    query = select(v)

    conditions = [v.c.days_overdue >= min_days_overdue]
    if school_id:
        conditions.append(v.c.school_id == str(school_id))

    query = query.where(and_(*conditions)).order_by(v.c.days_overdue.desc())

    result = await db.execute(query)
    rows = result.mappings().all()
    return [OverdueInvoiceResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/collections/daily",
    response_model=List[DailyCollectionResponse],
    summary="Get daily collections",
    description="Returns daily collection totals grouped by school and payment method.",
)
async def get_daily_collections(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_daily_collections
    query = select(v)

    conditions = []
    if school_id:
        conditions.append(v.c.school_id == str(school_id))
    if date_from:
        conditions.append(v.c.payment_date >= date_from)
    if date_to:
        conditions.append(v.c.payment_date <= date_to)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(v.c.payment_date.desc())

    result = await db.execute(query)
    rows = result.mappings().all()
    return [DailyCollectionResponse(**_row_to_dict(row)) for row in rows]


@router.get(
    "/revenue/monthly",
    response_model=List[MonthlyRevenueResponse],
    summary="Get monthly revenue",
    description="Returns monthly revenue statistics by school.",
)
async def get_monthly_revenue(
    school_id: Optional[UUID] = Query(None, description="Filter by school ID"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: AsyncSession = Depends(get_db),
    _current_user: TokenData = Depends(require_auth),
):
    v = v_monthly_revenue
    query = select(v)

    conditions = []
    if school_id:
        conditions.append(v.c.school_id == str(school_id))
    if year:
        conditions.append(func.extract("year", v.c.month) == year)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(v.c.month.desc())

    result = await db.execute(query)
    rows = result.mappings().all()
    return [MonthlyRevenueResponse(**_row_to_dict(row)) for row in rows]
