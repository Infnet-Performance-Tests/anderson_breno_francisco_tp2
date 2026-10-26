from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from routes.docs import DOCS_PATH, SWAGGER_CSS_URL, SWAGGER_JS_URL

BASE_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# Respostas JSON da API não carregam nenhum recurso: tudo bloqueado.
API_CSP = "default-src 'none'; frame-ancestors 'none'"

# ZAP TP3 — finding 10038 "Content Security Policy (CSP) Header Not Set" (Medium) em /docs
# — RESOLVIDO AQUI. No TP2 o /docs ficava sem CSP porque o Swagger UI padrão usa script
# inline. Agora (routes/docs.py) o init é um arquivo da própria origem, então a CSP do /docs
# libera só: scripts da própria origem e o bundle exato do Swagger no CDN, o CSS exato do
# Swagger, imagens inline (data:) e chamadas fetch para a própria API. Sem 'unsafe-inline'
# nem 'unsafe-eval'.
DOCS_CSP = (
    "default-src 'none'; "
    f"script-src 'self' {SWAGGER_JS_URL}; "
    f"style-src 'self' {SWAGGER_CSS_URL}; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)
# Ativa o isolamento cross-origin (COEP) no /docs: os arquivos do CDN são carregados em
# modo CORS (crossorigin="anonymous"), compatível com require-corp.
DOCS_HEADERS = {
    "Content-Security-Policy": DOCS_CSP,
    "Cross-Origin-Embedder-Policy": "require-corp",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.update(BASE_HEADERS)
        if request.url.path == DOCS_PATH:
            response.headers.update(DOCS_HEADERS)
        else:
            response.headers["Content-Security-Policy"] = API_CSP
        return response
