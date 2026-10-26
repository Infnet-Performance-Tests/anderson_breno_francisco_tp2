from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from domain.prediction import Intent
from models.requests import StrictRequest

TicketText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000),
]


class PredictionRequest(StrictRequest):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"text": "I was charged twice for my last order."}]}
    )

    text: TicketText = Field(
        description="Texto da mensagem do cliente (1 a 5.000 caracteres, sem campos extras).",
    )


class PredictionResponse(BaseModel):
    id: int = Field(description="Identificador da prediction salva para o usuário autenticado.")
    intent: Intent = Field(description="Intenção prevista (uma das classes de `Ticket Type`).")
    confidence: float = Field(ge=0.0, le=1.0, description="Confiança do modelo, de 0 a 1.")
    model_version: str = Field(description="Versão do modelo que gerou a resposta.")
