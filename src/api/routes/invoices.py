from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_invoice_service
from src.api.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceDetailResponse,
    InvoiceListResponse,
)
from src.application.services import InvoiceService
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus

router = APIRouter()


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    student_id: UUID = Query(None),
    school_id: UUID = Query(None),
    status: InvoiceStatus = Query(None),
    service: InvoiceService = Depends(get_invoice_service),
):
    skip = (page - 1) * page_size
    invoices = await service.get_all(
        skip=skip,
        limit=page_size,
        student_id=student_id,
        school_id=school_id,
        status=status,
    )
    total = await service.count(student_id=student_id, status=status)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    invoice_id: UUID,
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = await service.get_by_id(invoice_id)
        return InvoiceDetailResponse(
            id=invoice.id,
            student_id=invoice.student_id,
            amount=invoice.amount,
            due_date=invoice.due_date,
            description=invoice.description,
            status=invoice.status,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            paid_amount=invoice.paid_amount,
            pending_amount=invoice.pending_amount,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = await service.create(data.model_dump())
        return InvoiceResponse.model_validate(invoice)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = await service.update(invoice_id, data.model_dump(exclude_unset=True))
        return InvoiceResponse.model_validate(invoice)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{invoice_id}", response_model=InvoiceResponse)
async def cancel_invoice(
    invoice_id: UUID,
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = await service.cancel(invoice_id)
        return InvoiceResponse.model_validate(invoice)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
