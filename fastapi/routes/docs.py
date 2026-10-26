"""Documentação interativa (/docs) servida com SRI e CSP.

ZAP TP3 — finding 90003 "Sub Resource Integrity Attribute Missing" (Medium) — RESOLVIDO AQUI.
O /docs padrão do FastAPI carrega o Swagger UI do CDN em `swagger-ui-dist@5` (versão
flutuante) e sem atributo `integrity`. Se o CDN fosse comprometido, o JavaScript injetado
rodaria na origem da API com acesso ao token digitado em "Authorize". Esta página fixa a
versão exata e declara o hash SHA-384 de cada arquivo: o navegador recusa qualquer
conteúdo diferente do publicado.

O script de inicialização, que no FastAPI é inline, vira um arquivo da própria origem
(`/docs/swagger-init.js`), para que a CSP do /docs não precise de 'unsafe-inline'
(finding 10038, ver security/headers.py).
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

SWAGGER_UI_VERSION = "5.32.15"
SWAGGER_UI_CDN = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}"
SWAGGER_JS_URL = f"{SWAGGER_UI_CDN}/swagger-ui-bundle.js"
SWAGGER_CSS_URL = f"{SWAGGER_UI_CDN}/swagger-ui.css"
# Hashes gerados com: openssl dgst -sha384 -binary <arquivo> | openssl base64 -A
SWAGGER_JS_SRI = "sha384-m7zaGj7MPzU+G4lz2eyy73GxK9bbRDr9bB2CSdj8wodg2wu/Wnt6wsoLP3JD+RS9"
SWAGGER_CSS_SRI = "sha384-fgyWYkUAamzuI8mJFu/xpRP0JWCJRwkwUwsYDoOYVHUJ8NQE5cENn8ib3ppwFFSX"

DOCS_PATH = "/docs"
SWAGGER_INIT_PATH = "/docs/swagger-init.js"

SWAGGER_HTML = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Secure Support Agent Lab - Swagger UI</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="{SWAGGER_CSS_URL}"
      integrity="{SWAGGER_CSS_SRI}" crossorigin="anonymous">
</head>
<body>
<div id="swagger-ui"></div>
<script src="{SWAGGER_JS_URL}" integrity="{SWAGGER_JS_SRI}" crossorigin="anonymous"></script>
<script src="{SWAGGER_INIT_PATH}"></script>
</body>
</html>
"""

SWAGGER_INIT_JS = """window.ui = SwaggerUIBundle({
  url: "/openapi.json",
  dom_id: "#swagger-ui",
  layout: "BaseLayout",
  deepLinking: true,
  showExtensions: true,
  showCommonExtensions: true,
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
});
"""

router = APIRouter(include_in_schema=False)


@router.get(DOCS_PATH)
async def swagger_ui() -> HTMLResponse:
    return HTMLResponse(SWAGGER_HTML)


@router.get(SWAGGER_INIT_PATH)
async def swagger_init() -> Response:
    return Response(SWAGGER_INIT_JS, media_type="text/javascript")
