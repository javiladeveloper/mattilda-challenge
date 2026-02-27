from datetime import date
from typing import Optional
from uuid import UUID
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_school_service, get_student_service
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.api.schemas.school import (
    SchoolCreate,
    SchoolUpdate,
    SchoolResponse,
    SchoolListResponse,
)
from src.api.schemas.student import StudentResponse, StudentListResponse
from src.api.schemas.statements import (
    SchoolStatementResponse,
    InvoiceSummary,
    FinancialSummary,
    Period,
)
from src.application.services import SchoolService, StudentService
from src.domain.exceptions import EntityNotFoundError

router = APIRouter()


@router.get("", response_model=SchoolListResponse)
async def list_schools(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False),
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    skip = (page - 1) * page_size
    schools = await service.get_all(skip=skip, limit=page_size, active_only=active_only)
    total = await service.count(active_only=active_only)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return SchoolListResponse(
        items=[SchoolResponse.model_validate(s) for s in schools],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{school_id}", response_model=SchoolResponse)
async def get_school(
    school_id: UUID,
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        school = await service.get_by_id(school_id)
        return SchoolResponse.model_validate(school)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    data: SchoolCreate,
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    school = await service.create(data.model_dump())
    return SchoolResponse.model_validate(school)


@router.put("/{school_id}", response_model=SchoolResponse)
async def update_school(
    school_id: UUID,
    data: SchoolUpdate,
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        school = await service.update(school_id, data.model_dump(exclude_unset=True))
        return SchoolResponse.model_validate(school)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{school_id}", response_model=SchoolResponse)
async def delete_school(
    school_id: UUID,
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        school = await service.delete(school_id)
        return SchoolResponse.model_validate(school)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/{school_id}/students", response_model=StudentListResponse)
async def list_school_students(
    school_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    active_only: bool = Query(True),
    school_service: SchoolService = Depends(get_school_service),
    student_service: StudentService = Depends(get_student_service),
    _current_user: TokenData = Depends(require_auth),
):
    # Verify school exists
    try:
        await school_service.get_by_id(school_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    skip = (page - 1) * page_size
    students = await student_service.get_all(
        skip=skip, limit=page_size, school_id=school_id, active_only=active_only
    )
    total = await student_service.count(school_id=school_id, active_only=active_only)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return StudentListResponse(
        items=[StudentResponse.model_validate(s) for s in students],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{school_id}/statement", response_model=SchoolStatementResponse)
async def get_school_statement(
    school_id: UUID,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    service: SchoolService = Depends(get_school_service),
    _current_user: TokenData = Depends(require_auth),
):
    try:
        statement = await service.get_statement(school_id, from_date, to_date)

        return SchoolStatementResponse(
            school_id=statement.school_id,
            school_name=statement.school_name,
            period=Period(
                from_date=statement.period.from_date,
                to_date=statement.period.to_date,
            ),
            summary=FinancialSummary(
                total_invoiced=statement.summary.total_invoiced,
                total_paid=statement.summary.total_paid,
                total_pending=statement.summary.total_pending,
                total_overdue=statement.summary.total_overdue,
            ),
            total_students=statement.total_students,
            active_students=statement.active_students,
            invoices=[
                InvoiceSummary(
                    id=inv.id,
                    description=inv.description,
                    amount=inv.amount,
                    paid_amount=inv.paid_amount,
                    pending_amount=inv.pending_amount,
                    status=inv.status,
                    due_date=inv.due_date,
                    student_name=inv.student_name,
                )
                for inv in statement.invoices
            ],
            generated_at=statement.generated_at,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
