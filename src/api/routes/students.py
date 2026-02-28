from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_student_service, get_invoice_service
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.api.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentListResponse,
)
from src.api.schemas.invoice import InvoiceResponse, InvoiceListResponse
from src.api.schemas.statements import (
    StudentStatementResponse,
    InvoiceSummary,
    PaymentSummary,
    FinancialSummary,
)
from src.application.services import StudentService, InvoiceService
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus

router = APIRouter()


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    school_id: UUID = Query(None),
    active_only: bool = Query(False),
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    skip = (page - 1) * page_size
    students = await service.get_all(
        skip=skip, limit=page_size, school_id=school_id, active_only=active_only
    )
    total = await service.count(school_id=school_id, active_only=active_only)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return StudentListResponse(
        items=[StudentResponse.from_student(s) for s in students],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: UUID,
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        student = await service.get_by_id(student_id)
        return StudentResponse.from_student(student)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        student = await service.create(data.model_dump())
        return StudentResponse.from_student(student)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: UUID,
    data: StudentUpdate,
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        student = await service.update(student_id, data.model_dump(exclude_unset=True))
        return StudentResponse.from_student(student)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{student_id}", response_model=StudentResponse)
async def delete_student(
    student_id: UUID,
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        student = await service.delete(student_id)
        return StudentResponse.from_student(student)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/{student_id}/invoices", response_model=InvoiceListResponse)
async def list_student_invoices(
    student_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    invoice_status: InvoiceStatus = Query(None),
    student_service: StudentService = Depends(get_student_service),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    _current_user: TokenData = Depends(require_auth),
):
    # Verify student exists
    try:
        await student_service.get_by_id(student_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    skip = (page - 1) * page_size
    invoices = await invoice_service.get_all(
        skip=skip, limit=page_size, student_id=student_id, status=invoice_status
    )
    total = await invoice_service.count(student_id=student_id, status=invoice_status)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{student_id}/statement", response_model=StudentStatementResponse)
async def get_student_statement(
    student_id: UUID,
    service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        statement = await service.get_statement(student_id)

        return StudentStatementResponse(
            student_id=statement.student_id,
            student_name=statement.student_name,
            school_name=statement.school_name,
            summary=FinancialSummary(
                total_invoiced=statement.summary.total_invoiced,
                total_paid=statement.summary.total_paid,
                total_pending=statement.summary.total_pending,
                total_overdue=statement.summary.total_overdue,
            ),
            invoices=[
                InvoiceSummary(
                    id=inv.id,
                    description=inv.description,
                    amount=inv.amount,
                    paid_amount=inv.paid_amount,
                    pending_amount=inv.pending_amount,
                    status=inv.status,
                    due_date=inv.due_date,
                    payments=[
                        PaymentSummary(
                            amount=p.amount,
                            date=p.date,
                            method=p.method,
                        )
                        for p in (inv.payments or [])
                    ],
                )
                for inv in statement.invoices
            ],
            generated_at=statement.generated_at,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
