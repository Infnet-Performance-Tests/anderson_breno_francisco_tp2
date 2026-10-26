from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    """As cinco classes de `Ticket Type` formalizadas como alvo (y) no TP3."""

    BILLING_INQUIRY = "billing_inquiry"
    CANCELLATION_REQUEST = "cancellation_request"
    PRODUCT_INQUIRY = "product_inquiry"
    REFUND_REQUEST = "refund_request"
    TECHNICAL_ISSUE = "technical_issue"


@dataclass(frozen=True, slots=True)
class Prediction:
    intent: Intent
    confidence: float
    model_version: str
