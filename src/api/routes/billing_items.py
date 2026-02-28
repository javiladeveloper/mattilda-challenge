"""API routes for BillingItem management."""

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_billing_item_service, get_school_service
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.api.schemas.billing_item import (
    BillingItemCreate,
    BillingItemUpdate,
    BillingItemResponse,
    BillingItemListResponse,
)
from src.application.services import BillingItemService, SchoolService
from src.domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/billing-items", tags=["Billing Items"])


@router.get("", response_model=BillingItemListResponse)
async def list_billing_items(
    school_id: UUID = Query(..., description="School to list items for"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    recurring_only: Optional[bool] = Query(None, description="Filter by recurring status"),
    service: BillingItemService = Depends(get_billing_item_service),
    school_service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    """List all billing items for a school."""
    # Verify school exists
    try:
        await school_service.get_by_id(school_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    skip = (page - 1) * page_size
    items = await service.get_all(
        school_id=school_id,
        skip=skip,
        limit=page_size,
        active_only=active_only,
        recurring_only=recurring_only,
    )
    total = await service.count(
        school_id=school_id, active_only=active_only, recurring_only=recurring_only
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return BillingItemListResponse(
        items=[BillingItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/by-year", response_model=BillingItemListResponse)
async def list_billing_items_by_year(
    school_id: UUID = Query(..., description="School to list items for"),
    academic_year: str = Query(..., description="Academic year (e.g., '2024')"),
    active_only: bool = Query(True),
    service: BillingItemService = Depends(get_billing_item_service),
    school_service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    """List billing items for a specific academic year."""
    # Verify school exists
    try:
        await school_service.get_by_id(school_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    items = await service.get_by_academic_year(
        school_id=school_id, academic_year=academic_year, active_only=active_only
    )

    return BillingItemListResponse(
        items=[BillingItemResponse.model_validate(i) for i in items],
        total=len(items),
        page=1,
        page_size=len(items),
        pages=1,
    )


@router.get("/{item_id}", response_model=BillingItemResponse)
async def get_billing_item(
    item_id: UUID,
    service: BillingItemService = Depends(get_billing_item_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Get a billing item by ID."""
    try:
        item = await service.get_by_id(item_id)
        return BillingItemResponse.model_validate(item)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=BillingItemResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_item(
    data: BillingItemCreate,
    service: BillingItemService = Depends(get_billing_item_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Create a new billing item."""
    try:
        item = await service.create(data.model_dump())
        return BillingItemResponse.model_validate(item)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{item_id}", response_model=BillingItemResponse)
async def update_billing_item(
    item_id: UUID,
    data: BillingItemUpdate,
    service: BillingItemService = Depends(get_billing_item_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Update a billing item."""
    try:
        item = await service.update(item_id, data.model_dump(exclude_unset=True))
        return BillingItemResponse.model_validate(item)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{item_id}", response_model=BillingItemResponse)
async def delete_billing_item(
    item_id: UUID,
    service: BillingItemService = Depends(get_billing_item_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Soft delete a billing item."""
    try:
        item = await service.delete(item_id)
        return BillingItemResponse.model_validate(item)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
