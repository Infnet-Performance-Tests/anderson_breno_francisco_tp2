"""Rotas públicas: /health e a documentação interativa em /docs."""

import re


def test_health_retorna_ok(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_docs_esta_disponivel(client):
    resp = client.get("/docs")

    assert resp.status_code == 200
    assert "swagger-ui" in resp.text
    assert client.get("/docs/swagger-init.js").status_code == 200


def test_docs_tem_csp_restritiva(client):
    """Regressão do finding ZAP 10038 (CSP Header Not Set em /docs)."""
    csp = client.get("/docs").headers["content-security-policy"]

    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_docs_carrega_scripts_externos_com_sri(client):
    """Regressão do finding ZAP 90003 (Sub Resource Integrity Attribute Missing)."""
    html = client.get("/docs").text

    for tag in re.findall(r"<(?:script|link)[^>]+https://[^>]+>", html):
        assert 'integrity="sha384-' in tag
        assert 'crossorigin="anonymous"' in tag
    assert "<script>" not in html  # nenhum script inline


def test_redoc_foi_desligado(client):
    assert client.get("/redoc").status_code == 404


def test_openapi_documenta_autenticacao_e_respostas(client):
    spec = client.get("/openapi.json").json()

    assert "OAuth2PasswordBearer" in spec["components"]["securitySchemes"]
    for path, method in [
        ("/predict", "post"),
        ("/predictions", "get"),
        ("/predictions/{prediction_id}", "get"),
    ]:
        operation = spec["paths"][path][method]
        assert operation["description"]
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]
        assert "401" in operation["responses"]

    assert "429" in spec["paths"]["/auth/token"]["post"]["responses"]
    assert "404" in spec["paths"]["/predictions/{prediction_id}"]["get"]["responses"]
