from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_payment_service, get_invoice_service
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.api.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
)
from src.application.services import PaymentService, InvoiceService
from src.domain.exceptions import (
    EntityNotFoundError,
    PaymentExceedsDebtError,
    InvoiceCancelledError,
)
from src.domain.enums import PaymentMethod

router = APIRouter()


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    invoice_id: UUID = Query(None),
    method: PaymentMethod = Query(None),
    service: PaymentService = Depends(get_payment_service),
    _current_user: TokenData = Depends(require_auth),
):
    skip = (page - 1) * page_size
    payments = await service.get_all(
        skip=skip, limit=page_size, invoice_id=invoice_id, method=method
    )
    total = await service.count(invoice_id=invoice_id)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        payment = await service.get_by_id(payment_id)
        return PaymentResponse.model_validate(payment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentCreate,
    service: PaymentService = Depends(get_payment_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        payment = await service.create(data.model_dump(exclude_unset=True))
        return PaymentResponse.model_validate(payment)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except PaymentExceedsDebtError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except InvoiceCancelledError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/invoice/{invoice_id}", response_model=PaymentListResponse)
async def list_invoice_payments(
    invoice_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
    _current_user: TokenData = Depends(require_auth),
):
    # Verify invoice exists
    try:
        await invoice_service.get_by_id(invoice_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    skip = (page - 1) * page_size
    payments = await payment_service.get_all(skip=skip, limit=page_size, invoice_id=invoice_id)
    total = await payment_service.count(invoice_id=invoice_id)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
