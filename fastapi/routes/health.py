from fastapi import APIRouter

from models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar se a API está ativa",
    description='Rota pública, sem autenticação. Devolve `{"status": "ok"}`.',
)
async def health_check() -> HealthResponse:
    return HealthResponse()
