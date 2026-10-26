from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from routes import api_router
from routes.docs import router as docs_router
from security.headers import SecurityHeadersMiddleware
from security.rate_limit import limiter

DESCRIPTION = """
API de classificação de intenção para mensagens de atendimento ao cliente.

## Autenticação

1. Chame `POST /auth/token` com `username` e `password` (form-urlencoded).
2. Envie o token recebido em `Authorization: Bearer <token>`.
3. No Swagger, use o botão **Authorize** e informe usuário e senha.

Rotas marcadas com cadeado exigem token. Usuários de exemplo: `alice` / `alice123`,
`bob` / `bob123` e `admin` / `admin123` (credenciais acadêmicas).

## Controles de segurança

- Ownership em todas as rotas por ID (anti-BOLA): recurso de outro usuário devolve `404`.
- Bodies com `extra="forbid"`: campos não declarados devolvem `422`.
- Rate limit de 10 req/min por IP em `POST /auth/token` (`429` ao exceder).
- Headers HSTS, CSP, X-Frame-Options e X-Content-Type-Options em todas as respostas.
- CORS com allowlist explícita de origens.
"""

TAGS_METADATA = [
    {"name": "health", "description": "Verificação de disponibilidade. Pública."},
    {"name": "auth", "description": "Emissão de token JWT. Pública, com rate limit."},
    {"name": "prediction", "description": "Classificação de intenção. Exige token."},
    {"name": "predictions", "description": "Histórico do próprio usuário. Exige token."},
]


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        # /docs é servido por routes/docs.py (SRI + CSP, findings ZAP 90003 e 10038).
        # O /redoc foi desligado: duplicava a documentação com outro script de CDN sem SRI.
        docs_url=None,
        redoc_url=None,
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.include_router(api_router)
    application.include_router(docs_router)
    return application


app = create_app()
