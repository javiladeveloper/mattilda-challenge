"""AI Agent API endpoints for intelligent collection assistance."""

from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.rate_limiter import ai_rate_limiter
from src.api.auth.jwt import require_auth
from src.api.auth.models import TokenData
from src.ai.agent import CollectionAgent
from src.ai.schemas import (
    RiskAnalysisRequest,
    RiskAnalysisResponse,
    CollectionMessageRequest,
    CollectionMessageResponse,
    AssistantRequest,
    AssistantResponse,
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    SchoolMetrics,
    PaymentHistoryItem,
)
from src.application.services import StudentService, SchoolService, InvoiceService

router = APIRouter(prefix="/ai", tags=["AI Agent"])


def get_agent() -> CollectionAgent:
    """Get AI agent instance."""
    return CollectionAgent()


async def check_rate_limit(current_user: TokenData = Depends(require_auth)) -> dict:
    """Rate limit dependency for AI endpoints (per user)."""
    return await ai_rate_limiter.check_rate_limit(current_user.user_id)


# ============================================
# Risk Analysis
# ============================================


@router.post(
    "/risk-analysis/{student_id}",
    response_model=RiskAnalysisResponse,
    summary="Analyze payment risk",
    description="AI-powered analysis of a student's payment risk based on their history.",
)
async def analyze_student_risk(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    agent: CollectionAgent = Depends(get_agent),
    _rate_limit: dict = Depends(check_rate_limit),
):
    """
    Analyze payment risk for a specific student.

    The AI agent evaluates:
    - Payment history patterns
    - Overdue amounts
    - Payment timeliness
    - Overall account health

    Returns risk level (LOW, MEDIUM, HIGH, CRITICAL) with recommendations.
    """
    student_service = StudentService(db)

    # Get student with invoices and school (eager-loaded)
    student = await student_service.get_with_invoices(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} not found",
        )

    # Get student financials
    financials = await student_service.repo.get_student_financials(student_id)

    # Build payment history
    payment_history = []
    if student.invoices:
        for invoice in student.invoices:
            last_payment_date = None
            if invoice.payments:
                last_payment_date = max(p.payment_date for p in invoice.payments)

            days_late = 0
            if last_payment_date and last_payment_date > invoice.due_date:
                days_late = (last_payment_date - invoice.due_date).days

            payment_history.append(
                PaymentHistoryItem(
                    invoice_id=invoice.id,
                    amount=invoice.amount,
                    due_date=invoice.due_date,
                    paid_date=last_payment_date,
                    days_late=days_late,
                    status=invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status),
                )
            )

    # Build risk analysis request
    risk_request = RiskAnalysisRequest(
        student_id=student_id,
        student_name=student.full_name,
        school_name=student.school.name if student.school else "Unknown",
        total_invoiced=financials.get("total_invoiced", Decimal("0")),
        total_paid=financials.get("total_paid", Decimal("0")),
        total_pending=financials.get("total_pending", Decimal("0")),
        total_overdue=financials.get("total_overdue", Decimal("0")),
        payment_history=payment_history,
        enrolled_since=student.enrolled_at,
    )

    # Analyze risk
    return await agent.analyze_payment_risk(risk_request)


# ============================================
# Collection Messages
# ============================================


@router.post(
    "/collection-message",
    response_model=CollectionMessageResponse,
    summary="Generate collection message",
    description="Generate a personalized collection/reminder message.",
)
async def generate_collection_message(
    msg_request: CollectionMessageRequest,
    agent: CollectionAgent = Depends(get_agent),
    _rate_limit: dict = Depends(check_rate_limit),
):
    """
    Generate a personalized collection message.

    Supports different tones (FRIENDLY, FORMAL, URGENT, FINAL_NOTICE)
    and channels (EMAIL, SMS, WHATSAPP).

    The AI creates contextually appropriate messages in Spanish.
    """
    return await agent.generate_collection_message(msg_request)


@router.post(
    "/collection-message/{student_id}",
    response_model=CollectionMessageResponse,
    summary="Generate collection message for student",
    description="Generate a collection message using student's actual data.",
)
async def generate_student_collection_message(
    student_id: UUID,
    msg_request: CollectionMessageRequest,
    db: AsyncSession = Depends(get_db),
    agent: CollectionAgent = Depends(get_agent),
    _rate_limit: dict = Depends(check_rate_limit),
):
    """
    Generate a collection message for a specific student.

    Automatically fills in student and school information.
    """
    student_service = StudentService(db)

    # Use get_with_invoices to eager-load school relationship
    student = await student_service.get_with_invoices(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id} not found",
        )

    financials = await student_service.repo.get_student_financials(student_id)

    # Update request with actual data
    msg_request.student_name = student.full_name
    msg_request.school_name = student.school.name if student.school else "La escuela"
    msg_request.pending_amount = financials.get("total_pending", Decimal("0"))
    msg_request.overdue_amount = financials.get("total_overdue", Decimal("0"))

    return await agent.generate_collection_message(msg_request)


# ============================================
# Conversational Assistant
# ============================================


@router.post(
    "/assistant",
    response_model=AssistantResponse,
    summary="Ask the AI assistant",
    description="Conversational AI assistant for billing inquiries.",
)
async def ask_assistant(
    assistant_request: AssistantRequest,
    db: AsyncSession = Depends(get_db),
    agent: CollectionAgent = Depends(get_agent),
    _rate_limit: dict = Depends(check_rate_limit),
):
    """
    Ask the AI assistant about payments and accounts.

    The assistant can answer questions about:
    - Student balances
    - Pending and overdue invoices
    - Payment history
    - Collection processes
    - System usage

    Supports conversation history for context.
    """
    # If student_id or school_id provided, add context
    context_parts = []

    if assistant_request.student_id:
        student_service = StudentService(db)
        try:
            # Use get_with_invoices to eager-load school relationship
            student = await student_service.get_with_invoices(assistant_request.student_id)
            if student:
                financials = await student_service.repo.get_student_financials(assistant_request.student_id)
                context_parts.append(
                    f"Estudiante: {student.full_name}\n"
                    f"Escuela: {student.school.name if student.school else 'N/A'}\n"
                    f"Total facturado: ${financials.get('total_invoiced', 0)}\n"
                    f"Total pagado: ${financials.get('total_paid', 0)}\n"
                    f"Pendiente: ${financials.get('total_pending', 0)}\n"
                    f"Vencido: ${financials.get('total_overdue', 0)}"
                )
        except Exception:
            pass

    if assistant_request.school_id:
        school_service = SchoolService(db)
        try:
            school = await school_service.get_by_id(assistant_request.school_id)
            financials = await school_service.repo.get_school_financials(assistant_request.school_id)
            student_count = await school_service.repo.get_student_count(assistant_request.school_id)
            context_parts.append(
                f"Escuela: {school.name}\n"
                f"Estudiantes activos: {student_count}\n"
                f"Total facturado: ${financials.get('total_invoiced', 0)}\n"
                f"Total cobrado: ${financials.get('total_paid', 0)}\n"
                f"Pendiente: ${financials.get('total_pending', 0)}\n"
                f"Vencido: ${financials.get('total_overdue', 0)}"
            )
        except Exception:
            pass

    if context_parts:
        assistant_request.context = "\n\n".join(context_parts)

    return await agent.answer_question(assistant_request)


# ============================================
# Executive Summary
# ============================================


@router.post(
    "/executive-summary",
    response_model=ExecutiveSummaryResponse,
    summary="Generate executive summary",
    description="AI-generated executive summary with insights and recommendations.",
)
async def generate_executive_summary(
    summary_request: ExecutiveSummaryRequest,
    db: AsyncSession = Depends(get_db),
    agent: CollectionAgent = Depends(get_agent),
    _rate_limit: dict = Depends(check_rate_limit),
):
    """
    Generate an AI-powered executive summary.

    Provides:
    - Key metrics overview
    - Highlights and concerns
    - Trend analysis
    - Actionable recommendations
    - Narrative summary

    Can be generated for a specific school or all schools.
    """
    school_service = SchoolService(db)

    if summary_request.school_id:
        # Single school summary
        try:
            school = await school_service.get_by_id(summary_request.school_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"School {summary_request.school_id} not found",
            )

        financials = await school_service.repo.get_school_financials(summary_request.school_id)
        total_students = await school_service.repo.get_student_count(
            summary_request.school_id, active_only=False
        )
        active_students = await school_service.repo.get_student_count(
            summary_request.school_id, active_only=True
        )

        total_invoiced = financials.get("total_invoiced", Decimal("0"))
        total_paid = financials.get("total_paid", Decimal("0"))

        metrics = SchoolMetrics(
            school_id=school.id,
            school_name=school.name,
            total_students=total_students,
            active_students=active_students,
            total_invoiced=total_invoiced,
            total_collected=total_paid,
            total_pending=financials.get("total_pending", Decimal("0")),
            total_overdue=financials.get("total_overdue", Decimal("0")),
            collection_rate=float(total_paid / total_invoiced) if total_invoiced > 0 else 0,
        )
    else:
        # All schools summary (aggregate)
        schools = await school_service.get_all(limit=1000)

        total_students = 0
        active_students = 0
        total_invoiced = Decimal("0")
        total_paid = Decimal("0")
        total_pending = Decimal("0")
        total_overdue = Decimal("0")

        for school in schools:
            financials = await school_service.repo.get_school_financials(school.id)
            total_students += await school_service.repo.get_student_count(
                school.id, active_only=False
            )
            active_students += await school_service.repo.get_student_count(
                school.id, active_only=True
            )
            total_invoiced += financials.get("total_invoiced", Decimal("0"))
            total_paid += financials.get("total_paid", Decimal("0"))
            total_pending += financials.get("total_pending", Decimal("0"))
            total_overdue += financials.get("total_overdue", Decimal("0"))

        metrics = SchoolMetrics(
            school_id=schools[0].id if schools else UUID("00000000-0000-0000-0000-000000000000"),
            school_name="Todas las escuelas",
            total_students=total_students,
            active_students=active_students,
            total_invoiced=total_invoiced,
            total_collected=total_paid,
            total_pending=total_pending,
            total_overdue=total_overdue,
            collection_rate=float(total_paid / total_invoiced) if total_invoiced > 0 else 0,
        )

    return await agent.generate_executive_summary(summary_request, metrics)


# ============================================
# Health Check
# ============================================


@router.get(
    "/status",
    summary="AI Agent status",
    description="Check if AI agent is available and configured.",
)
async def ai_status(agent: CollectionAgent = Depends(get_agent)):
    """Check AI agent availability."""
    is_available = agent._is_available()
    return {
        "ai_available": is_available,
        "model": agent.model if is_available else None,
        "fallback_mode": not is_available,
        "message": (
            "AI agent is ready" if is_available else "AI agent running in fallback mode (no API key)"
        ),
    }
