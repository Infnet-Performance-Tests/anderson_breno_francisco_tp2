from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

import crud
from application.prediction_facade import prediction_facade
from database import get_session
from models.prediction import PredictionRequest, PredictionResponse
from routes.responses import UNAUTHORIZED
from security.dependencies import CurrentUser

router = APIRouter(tags=["prediction"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Classificar a intenção de uma mensagem",
    description=(
        "**Requer autenticação** (`Authorization: Bearer <token>`).\n\n"
        "Recebe o texto da mensagem do cliente e devolve a intenção prevista. A prediction é "
        "gravada com `owner_id` igual ao usuário autenticado e pode ser consultada depois em "
        "`GET /predictions/{prediction_id}`.\n\n"
        "O body aceita **somente** o campo `text`; qualquer campo extra devolve `422`. "
        "Enquanto o classificador não é treinado, a resposta vem de um stub (`stub-v0`)."
    ),
    responses={
        **UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Texto vazio, maior que 5.000 caracteres ou campo extra no body."
        },
    },
)
async def predict_intent(
    request: PredictionRequest,
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PredictionResponse:
    prediction = prediction_facade.predict(request.text)
    stored = crud.create_prediction(
        session,
        owner_id=current_user.id,
        text=request.text,
        intent=prediction.intent,
        confidence=prediction.confidence,
    )
    return PredictionResponse(
        id=stored.id,
        intent=prediction.intent,
        confidence=prediction.confidence,
        model_version=prediction.model_version,
    )
