"""Reports API endpoints - Exposes database views for analytics."""

from typing import List, Optional, Any
from datetime import date
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


def convert_row_to_dict(row) -> dict:
    """Convert a database row to a dictionary with proper type conversion."""
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


# ============================================
# Response Schemas
# ============================================

class StudentBalanceResponse(BaseModel):
    """Student balance summary."""
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
    """School financial summary."""
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
    """Detailed invoice information."""
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
    """Payment history record."""
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
    """Overdue invoice for collections."""
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
    """Daily collection summary."""
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
    """Monthly revenue summary."""
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


# ============================================
# Endpoints
# ============================================

@router.get(
    "/students/balance",
    response_model=List[StudentBalanceResponse],
    summary="Get student balances",
    description="Returns balance summary for all students including total invoiced, paid, and pending amounts."
)
async def get_student_balances(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    only_with_debt: bool = Query(False, description="Only show students with balance > 0"),
    only_active: bool = Query(True, description="Only show active students"),
    db: AsyncSession = Depends(get_db)
):
    """Get balance summary for all students."""
    query = "SELECT * FROM v_student_balance WHERE 1=1"
    params = {}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    if only_with_debt:
        query += " AND balance_due > 0"

    if only_active:
        query += " AND is_active = true"

    query += " ORDER BY balance_due DESC"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [StudentBalanceResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/schools/summary",
    response_model=List[SchoolSummaryResponse],
    summary="Get school summaries",
    description="Returns financial summary for all schools including totals and invoice counts."
)
async def get_school_summaries(
    only_active: bool = Query(True, description="Only show active schools"),
    db: AsyncSession = Depends(get_db)
):
    """Get financial summary for all schools."""
    query = "SELECT * FROM v_school_summary"

    if only_active:
        query += " WHERE is_active = true"

    query += " ORDER BY school_name"

    result = await db.execute(text(query))
    rows = result.mappings().all()
    return [SchoolSummaryResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/invoices/details",
    response_model=List[InvoiceDetailResponse],
    summary="Get invoice details",
    description="Returns detailed information for all invoices including payment status."
)
async def get_invoice_details(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, PARTIAL, PAID, OVERDUE, CANCELLED)"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information for all invoices."""
    query = "SELECT * FROM v_invoice_details WHERE 1=1"
    params = {}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    if student_id:
        query += " AND student_id = :student_id"
        params["student_id"] = student_id

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY due_date DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [InvoiceDetailResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/payments/history",
    response_model=List[PaymentHistoryResponse],
    summary="Get payment history",
    description="Returns complete payment history with all related details."
)
async def get_payment_history(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip results"),
    db: AsyncSession = Depends(get_db)
):
    """Get complete payment history."""
    query = "SELECT * FROM v_payment_history WHERE 1=1"
    params = {}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    if student_id:
        query += " AND student_id = :student_id"
        params["student_id"] = student_id

    if date_from:
        query += " AND payment_date >= :date_from"
        params["date_from"] = date_from

    if date_to:
        query += " AND payment_date <= :date_to"
        params["date_to"] = date_to

    query += " ORDER BY payment_created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [PaymentHistoryResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/invoices/overdue",
    response_model=List[OverdueInvoiceResponse],
    summary="Get overdue invoices",
    description="Returns all overdue invoices for collections follow-up."
)
async def get_overdue_invoices(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    min_days_overdue: int = Query(0, ge=0, description="Minimum days overdue"),
    db: AsyncSession = Depends(get_db)
):
    """Get all overdue invoices for collections."""
    query = "SELECT * FROM v_overdue_invoices WHERE days_overdue >= :min_days"
    params = {"min_days": min_days_overdue}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    query += " ORDER BY days_overdue DESC"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [OverdueInvoiceResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/collections/daily",
    response_model=List[DailyCollectionResponse],
    summary="Get daily collections",
    description="Returns daily collection totals grouped by school and payment method."
)
async def get_daily_collections(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db)
):
    """Get daily collection report."""
    query = "SELECT * FROM v_daily_collections WHERE 1=1"
    params = {}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    if date_from:
        query += " AND payment_date >= :date_from"
        params["date_from"] = date_from

    if date_to:
        query += " AND payment_date <= :date_to"
        params["date_to"] = date_to

    query += " ORDER BY payment_date DESC"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [DailyCollectionResponse(**convert_row_to_dict(row)) for row in rows]


@router.get(
    "/revenue/monthly",
    response_model=List[MonthlyRevenueResponse],
    summary="Get monthly revenue",
    description="Returns monthly revenue statistics by school."
)
async def get_monthly_revenue(
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: AsyncSession = Depends(get_db)
):
    """Get monthly revenue report."""
    query = "SELECT * FROM v_monthly_revenue WHERE 1=1"
    params = {}

    if school_id:
        query += " AND school_id = :school_id"
        params["school_id"] = school_id

    if year:
        query += " AND EXTRACT(YEAR FROM month) = :year"
        params["year"] = year

    query += " ORDER BY month DESC"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [MonthlyRevenueResponse(**convert_row_to_dict(row)) for row in rows]
