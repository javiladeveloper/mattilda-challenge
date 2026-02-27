"""AI Module for Mattilda - Intelligent Collection Agent."""

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
)

__all__ = [
    "CollectionAgent",
    "RiskAnalysisRequest",
    "RiskAnalysisResponse",
    "CollectionMessageRequest",
    "CollectionMessageResponse",
    "AssistantRequest",
    "AssistantResponse",
    "ExecutiveSummaryRequest",
    "ExecutiveSummaryResponse",
]
