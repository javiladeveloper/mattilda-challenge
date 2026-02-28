"""API routes for Grade management."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_grade_service, get_school_service
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.api.schemas.grade import (
    GradeCreate,
    GradeUpdate,
    GradeResponse,
    GradeListResponse,
)
from src.application.services import GradeService, SchoolService
from src.domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.get("", response_model=GradeListResponse)
async def list_grades(
    school_id: UUID = Query(..., description="School to list grades for"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    service: GradeService = Depends(get_grade_service),
    school_service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    """List all grades for a school."""
    # Verify school exists
    try:
        await school_service.get_by_id(school_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    skip = (page - 1) * page_size
    grades = await service.get_all(
        school_id=school_id, skip=skip, limit=page_size, active_only=active_only
    )
    total = await service.count(school_id=school_id, active_only=active_only)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return GradeListResponse(
        items=[GradeResponse.model_validate(g) for g in grades],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{grade_id}", response_model=GradeResponse)
async def get_grade(
    grade_id: UUID,
    service: GradeService = Depends(get_grade_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Get a grade by ID."""
    try:
        grade = await service.get_by_id(grade_id)
        return GradeResponse.model_validate(grade)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def create_grade(
    data: GradeCreate,
    service: GradeService = Depends(get_grade_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Create a new grade."""
    try:
        grade = await service.create(data.model_dump())
        return GradeResponse.model_validate(grade)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{grade_id}", response_model=GradeResponse)
async def update_grade(
    grade_id: UUID,
    data: GradeUpdate,
    service: GradeService = Depends(get_grade_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Update a grade."""
    try:
        grade = await service.update(grade_id, data.model_dump(exclude_unset=True))
        return GradeResponse.model_validate(grade)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{grade_id}", response_model=GradeResponse)
async def delete_grade(
    grade_id: UUID,
    service: GradeService = Depends(get_grade_service),
    _current_user: TokenData = Depends(require_auth),
):
    """Soft delete a grade."""
    try:
        grade = await service.delete(grade_id)
        return GradeResponse.model_validate(grade)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
