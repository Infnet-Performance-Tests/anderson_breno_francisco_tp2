"""Segurança — autenticação: credenciais válidas e inválidas em POST /auth/token."""

from datetime import UTC, datetime, timedelta

import jwt

from config import settings
from conftest import login

GENERIC_ERROR = {"detail": "Incorrect username or password"}


def _token(payload, key=None, algorithm=None):
    return jwt.encode(
        payload, key or settings.jwt_secret_key, algorithm=algorithm or settings.jwt_algorithm
    )


def test_credenciais_validas_devolvem_jwt_do_proprio_usuario(client):
    resp = login(client, "alice", "alice123")

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(
        body["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert claims["sub"] == "alice"
    assert {"iat", "exp"} <= claims.keys()


def test_senha_incorreta_e_recusada_com_401_generico(client):
    resp = login(client, "alice", "senha-errada")

    assert resp.status_code == 401
    assert resp.json() == GENERIC_ERROR
    assert resp.headers["www-authenticate"] == "Bearer"
    assert "access_token" not in resp.text


def test_usuario_inexistente_tem_a_mesma_resposta_de_senha_incorreta(client):
    """A resposta não pode revelar quais usernames existem (enumeração de usuários)."""
    inexistente = login(client, "mallory", "qualquer")
    senha_errada = login(client, "bob", "qualquer")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json() == senha_errada.json() == GENERIC_ERROR


def test_senha_de_outro_usuario_nao_autentica(client):
    resp = login(client, "bob", "alice123")

    assert resp.status_code == 401


def test_token_assinado_com_outra_chave_e_recusado(client):
    now = datetime.now(UTC)
    forjado = _token(
        {"sub": "alice", "iat": now, "exp": now + timedelta(minutes=5)},
        key="chave-do-atacante-com-32-bytes-ou-mais",
    )

    resp = client.get("/predictions", headers={"Authorization": f"Bearer {forjado}"})

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_token_expirado_e_recusado(client):
    past = datetime.now(UTC) - timedelta(hours=1)
    expirado = _token({"sub": "alice", "iat": past, "exp": past + timedelta(minutes=30)})

    resp = client.get("/predictions", headers={"Authorization": f"Bearer {expirado}"})

    assert resp.status_code == 401


def test_token_valido_de_usuario_que_nao_existe_no_banco_e_recusado(client):
    now = datetime.now(UTC)
    fantasma = _token({"sub": "ghost", "iat": now, "exp": now + timedelta(minutes=5)})

    resp = client.get("/predictions", headers={"Authorization": f"Bearer {fantasma}"})

    assert resp.status_code == 401
