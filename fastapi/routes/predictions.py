from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlmodel import Session

import crud
from database import get_session
from models.responses import PredictionRead
from routes.responses import NOT_FOUND, UNAUTHORIZED
from security.dependencies import CurrentUser

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get(
    "",
    response_model=list[PredictionRead],
    summary="Listar as predictions do usuário autenticado",
    description=(
        "**Requer autenticação.** Devolve apenas as predictions cujo `owner_id` é o usuário "
        "do token; recursos de outros usuários nunca aparecem na lista."
    ),
    responses=UNAUTHORIZED,
)
async def list_my_predictions(
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> list[PredictionRead]:
    predictions = crud.list_predictions_by_owner(session, current_user.id)
    return [PredictionRead.model_validate(p) for p in predictions]


@router.get(
    "/{prediction_id}",
    response_model=PredictionRead,
    summary="Consultar uma prediction por ID",
    description=(
        "**Requer autenticação.** O ownership é verificado na própria consulta ao banco "
        "(`id` **e** `owner_id`). Se a prediction pertencer a outro usuário, a resposta é "
        "`404`, idêntica à de um ID inexistente."
    ),
    responses={**UNAUTHORIZED, **NOT_FOUND},
)
async def get_my_prediction(
    prediction_id: Annotated[int, Path(ge=1, description="ID da prediction.")],
    current_user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> PredictionRead:
    # Anti-BOLA: nunca buscar só pelo ID e checar o dono depois.
    prediction = crud.get_prediction_for_owner(session, prediction_id, current_user.id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return PredictionRead.model_validate(prediction)
