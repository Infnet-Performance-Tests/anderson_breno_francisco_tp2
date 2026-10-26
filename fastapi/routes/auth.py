from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from application.auth_facade import auth_facade
from config import settings
from database import get_session
from models.auth import TokenResponse
from models.responses import ErrorResponse, RateLimitResponse
from security.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Autenticar e obter um token JWT",
    description=(
        "Recebe `username` e `password` como **form-urlencoded** (padrão OAuth2 password flow) "
        "e devolve um JWT assinado (HS256) válido por 30 minutos.\n\n"
        "- Rota pública: não exige token.\n"
        "- **Rate limit:** 10 requisições por minuto por IP (SlowAPI); a 11ª recebe `429`.\n"
        "- A mensagem de erro é genérica e não indica se o usuário existe."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Usuário inexistente, inativo ou senha incorreta.",
            "content": {
                "application/json": {"example": {"detail": "Incorrect username or password"}}
            },
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Formulário sem `username` ou `password`."
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": RateLimitResponse,
            "description": "Mais de 10 tentativas no último minuto a partir do mesmo IP.",
            "content": {
                "application/json": {"example": {"error": "Rate limit exceeded: 10 per 1 minute"}}
            },
        },
    },
)
@limiter.limit(settings.auth_rate_limit)
async def issue_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
) -> TokenResponse:
    access_token = auth_facade.authenticate(session, form_data.username, form_data.password)
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=access_token)
