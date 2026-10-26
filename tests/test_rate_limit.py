"""Segurança — rate limiting: POST /auth/token aceita 10 req/min por cliente (SlowAPI)."""

from conftest import login

ATTEMPTS_ALLOWED_PER_MINUTE = 10


def test_auth_token_devolve_429_apos_exceder_o_limite(client):
    for _ in range(ATTEMPTS_ALLOWED_PER_MINUTE):
        assert login(client, "admin", "errada").status_code == 401

    resp = login(client, "admin", "errada")

    assert resp.status_code == 429
    assert resp.json() == {"error": "Rate limit exceeded: 10 per 1 minute"}


def test_bloqueio_vale_mesmo_para_credencial_correta(client):
    """Depois do limite, nem a senha certa passa: o atacante não descobre se acertou."""
    for _ in range(ATTEMPTS_ALLOWED_PER_MINUTE):
        login(client, "alice", "errada")

    resp = login(client, "alice", "alice123")

    assert resp.status_code == 429
    assert "access_token" not in resp.text


def test_limite_nao_afeta_outras_rotas(client):
    for _ in range(ATTEMPTS_ALLOWED_PER_MINUTE + 1):
        login(client, "admin", "errada")

    assert client.get("/health").status_code == 200
