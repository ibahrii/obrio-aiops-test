"""Pydantic output schemas for both tasks."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal[
    "billing_subscription",
    "refund_request",
    "technical_issue",
    "account_access",
    "expert_complaint",
    "product_question",
    "privacy_legal",
    "safety_wellbeing",
    "feedback_other",
]
CATEGORIES: list[str] = list(Category.__args__)  # type: ignore[attr-defined]

Priority = Literal["P1", "P2", "P3", "P4"]
Route = Literal[
    "Billing", "Tech", "Expert Quality", "Trust & Safety",
    "Legal & Privacy", "Expert Ops", "General Support",
]
Sentiment = Literal["calm", "frustrated", "angry", "distressed"]
RequesterType = Literal["user", "expert", "unknown"]


class NextStep(BaseModel):
    route_to: Route
    action: str = Field(description="Short next action for the support team")


class ClassifierOutput(BaseModel):
    """What the model must return (validated before use)."""
    category: Category
    secondary_category: Optional[Category] = None
    priority: Priority
    requester_type: RequesterType
    language: str = Field(description="ISO 639-1 code of the ticket language")
    sentiment: Sentiment
    next_step: NextStep
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool
    human_reasons: list[str] = Field(default_factory=list)
    rationale: str


class ClassificationResult(BaseModel):
    """Final result after code-level guards. Category may be 'unclassified' (safe default)."""
    category: str
    secondary_category: Optional[str] = None
    priority: Priority
    requester_type: RequesterType = "unknown"
    language: str = "unknown"
    sentiment: str = "calm"
    next_step: NextStep
    confidence: float = 0.0
    needs_human: bool
    human_reasons: list[str] = Field(default_factory=list)
    rationale: str = ""
    guard_overrides: list[str] = Field(default_factory=list, description="What code changed vs model output")
    meta: dict = Field(default_factory=dict, description="model, latency, tokens, cache, fallbacks")


class Citation(BaseModel):
    article_id: str
    quote: str


class Replies(BaseModel):
    formal: str
    empathetic: str
    short: str


class AssistantOutput(BaseModel):
    summary: str
    replies: Replies
    citations: list[Citation] = Field(default_factory=list)
    reply_language: str
    kb_has_answer: bool = Field(description="False if the retrieved articles do not answer the ticket")
    human_decision_required: bool
    reasons: list[str] = Field(default_factory=list)


class AssistantResult(BaseModel):
    summary: str
    replies: Replies
    citations: list[dict] = Field(default_factory=list)  # + "valid": bool
    reply_language: str
    kb_has_answer: bool
    human_decision_required: bool
    reasons: list[str] = Field(default_factory=list)
    checks: dict = Field(default_factory=dict)  # length/language/citation checks
    classification: Optional[ClassificationResult] = None
    retrieved: list[dict] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
