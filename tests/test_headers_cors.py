"""Segurança — headers HTTP e CORS (migrados de fastapi/tests no TP3)."""

from config import settings

REQUIRED_HEADERS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
}


def test_headers_de_seguranca_em_respostas_de_sucesso(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    for name, value in REQUIRED_HEADERS.items():
        assert resp.headers[name] == value


def test_headers_de_seguranca_em_respostas_de_erro(client):
    resp = client.post("/predict", json={"text": "I need a refund"})

    assert resp.status_code == 401
    for name, value in REQUIRED_HEADERS.items():
        assert resp.headers[name] == value


def _preflight(client, origin):
    return client.options(
        "/auth/token",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )


def test_cors_permite_origem_da_allowlist(client):
    allowed_origin = settings.allowed_origins[0]

    resp = _preflight(client, allowed_origin)

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == allowed_origin


def test_cors_recusa_origem_fora_da_allowlist(client):
    resp = _preflight(client, "https://evil.example.com")

    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_allowlist_de_cors_nao_tem_curinga():
    assert "*" not in settings.allowed_origins
