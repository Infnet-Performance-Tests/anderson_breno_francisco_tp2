"""Modelos Pydantic de SAÍDA."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    intent: str
    confidence: float
    created_at: datetime


class ErrorResponse(BaseModel):
    """Corpo padrão de erro do FastAPI (`HTTPException`)."""

    detail: str


class RateLimitResponse(BaseModel):
    """Corpo devolvido pelo SlowAPI quando o limite é excedido."""

    error: str
