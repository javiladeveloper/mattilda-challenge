"""Pydantic schemas for AI Agent requests and responses."""

from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MessageTone(str, Enum):
    """Tone for collection messages."""

    FRIENDLY = "FRIENDLY"
    FORMAL = "FORMAL"
    URGENT = "URGENT"
    FINAL_NOTICE = "FINAL_NOTICE"


class MessageChannel(str, Enum):
    """Communication channel for messages."""

    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


# ============================================
# Risk Analysis
# ============================================


class PaymentHistoryItem(BaseModel):
    """Payment history item for risk analysis."""

    invoice_id: UUID
    amount: Decimal
    due_date: date
    paid_date: Optional[date] = None
    days_late: int = 0
    status: str


class RiskAnalysisRequest(BaseModel):
    """Request for student payment risk analysis."""

    student_id: UUID
    student_name: str
    school_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    total_overdue: Decimal
    payment_history: List[PaymentHistoryItem] = []
    enrolled_since: Optional[date] = None


class RiskFactor(BaseModel):
    """Individual risk factor identified."""

    factor: str
    impact: str  # LOW, MEDIUM, HIGH
    description: str


class RiskAnalysisResponse(BaseModel):
    """Response with risk analysis results."""

    student_id: UUID
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100, description="Risk score 0-100")
    risk_factors: List[RiskFactor] = []
    recommendations: List[str] = []
    predicted_payment_probability: float = Field(
        ge=0, le=1, description="Probability of payment in next 30 days"
    )
    suggested_action: str
    analysis_summary: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Collection Messages
# ============================================


class CollectionMessageRequest(BaseModel):
    """Request to generate a collection message."""

    student_name: str
    parent_name: Optional[str] = None
    school_name: str
    pending_amount: Decimal
    overdue_amount: Decimal = Decimal("0")
    days_overdue: int = 0
    invoices_pending: int = 1
    tone: MessageTone = MessageTone.FRIENDLY
    channel: MessageChannel = MessageChannel.EMAIL
    language: str = "es"  # Spanish by default
    include_payment_link: bool = True
    custom_context: Optional[str] = None


class CollectionMessageResponse(BaseModel):
    """Generated collection message."""

    subject: Optional[str] = None  # For email
    message: str
    tone_used: MessageTone
    channel: MessageChannel
    call_to_action: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Assistant (Conversational)
# ============================================


class ConversationMessage(BaseModel):
    """A message in the conversation history."""

    role: str  # "user" or "assistant"
    content: str


class AssistantRequest(BaseModel):
    """Request for the conversational assistant."""

    question: str
    student_id: Optional[UUID] = None
    school_id: Optional[UUID] = None
    context: Optional[str] = None
    conversation_history: List[ConversationMessage] = []
    language: str = "es"


class AssistantResponse(BaseModel):
    """Response from the conversational assistant."""

    answer: str
    suggested_actions: List[str] = []
    related_topics: List[str] = []
    confidence: float = Field(ge=0, le=1)
    requires_human_followup: bool = False
    responded_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Executive Summary
# ============================================


class SchoolMetrics(BaseModel):
    """Metrics for a school."""

    school_id: UUID
    school_name: str
    total_students: int
    active_students: int
    total_invoiced: Decimal
    total_collected: Decimal
    total_pending: Decimal
    total_overdue: Decimal
    collection_rate: float


class ExecutiveSummaryRequest(BaseModel):
    """Request for executive summary generation."""

    school_id: Optional[UUID] = None  # None for all schools
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    include_recommendations: bool = True
    include_trends: bool = True
    language: str = "es"


class TrendInsight(BaseModel):
    """A trend insight identified by AI."""

    trend: str
    direction: str  # "UP", "DOWN", "STABLE"
    impact: str
    description: str


class ExecutiveSummaryResponse(BaseModel):
    """AI-generated executive summary."""

    title: str
    period: str
    key_metrics: dict
    highlights: List[str]
    concerns: List[str]
    trends: List[TrendInsight] = []
    recommendations: List[str] = []
    narrative_summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
