from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from src.domain.entities.school import School
from src.domain.interfaces.unit_of_work import UnitOfWork
from src.domain.exceptions import EntityNotFoundError
from src.domain.enums import InvoiceStatus
from src.application.dto.statements import (
    SchoolStatementDTO,
    InvoiceSummaryDTO,
    FinancialSummaryDTO,
    PeriodDTO,
)


class SchoolService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_all(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[School]:
        filters = {"is_active": True} if active_only else None
        return await self._uow.schools.get_all(skip=skip, limit=limit, filters=filters)

    async def get_by_id(self, school_id: UUID) -> School:
        school = await self._uow.schools.get_by_id(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)
        return school

    async def create(self, data: dict) -> School:
        school = School(**data)
        saved = await self._uow.schools.save(school)
        self._uow.track(school)
        await self._uow.commit()
        return saved

    async def update(self, school_id: UUID, data: dict) -> School:
        school = await self._uow.schools.get_by_id(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)
        school.update(**data)
        saved = await self._uow.schools.save(school)
        self._uow.track(school)
        await self._uow.commit()
        return saved

    async def delete(self, school_id: UUID) -> School:
        school = await self._uow.schools.get_by_id(school_id)
        if not school:
            raise EntityNotFoundError("School", school_id)
        school.deactivate()
        saved = await self._uow.schools.save(school)
        self._uow.track(school)
        await self._uow.commit()
        return saved

    async def count(self, active_only: bool = False) -> int:
        filters = {"is_active": True} if active_only else None
        return await self._uow.schools.count(filters)

    async def get_statement(
        self,
        school_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> SchoolStatementDTO:
        school = await self.get_by_id(school_id)

        await self._uow.invoices.update_overdue_status()
        await self._uow.commit()

        total_students = await self._uow.schools.get_student_count(school_id, active_only=False)
        active_students = await self._uow.schools.get_student_count(school_id, active_only=True)
        financials = await self._uow.schools.get_school_financials(school_id)

        invoice_details = await self._uow.invoices.get_by_school_with_details(school_id)

        invoice_summaries = []
        for inv in invoice_details:
            if from_date and inv["created_at"].date() < from_date:
                continue
            if to_date and inv["created_at"].date() > to_date:
                continue

            invoice_summaries.append(
                InvoiceSummaryDTO(
                    id=inv["id"],
                    description=inv["description"],
                    amount=inv["amount"],
                    paid_amount=inv["paid_amount"],
                    pending_amount=inv["pending_amount"],
                    status=inv["status"],
                    due_date=inv["due_date"],
                    student_name=inv["student_name"],
                )
            )

        return SchoolStatementDTO(
            school_id=school.id,
            school_name=school.name,
            period=PeriodDTO(from_date=from_date, to_date=to_date),
            summary=FinancialSummaryDTO(
                total_invoiced=financials["total_invoiced"],
                total_paid=financials["total_paid"],
                total_pending=financials["total_pending"],
                total_overdue=financials["total_overdue"],
            ),
            total_students=total_students,
            active_students=active_students,
            invoices=invoice_summaries,
            generated_at=datetime.utcnow(),
        )
