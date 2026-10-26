"""Segurança — rota protegida: nenhuma rota autenticada responde sem token válido."""

import pytest

PROTECTED_ROUTES = [
    ("post", "/predict", {"json": {"text": "hello"}}),
    ("get", "/predictions", {}),
    ("get", "/predictions/1", {}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_ROUTES)
def test_rota_protegida_sem_token_e_negada(client, method, path, kwargs):
    resp = getattr(client, method)(path, **kwargs)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Not authenticated"}
    assert resp.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_ROUTES)
def test_rota_protegida_com_token_invalido_e_negada(client, method, path, kwargs):
    headers = {"Authorization": "Bearer token.invalido"}

    resp = getattr(client, method)(path, headers=headers, **kwargs)

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Could not validate credentials"}


def test_esquema_diferente_de_bearer_e_negado(client):
    resp = client.get("/predictions", headers={"Authorization": "Basic YWxpY2U6YWxpY2UxMjM="})

    assert resp.status_code == 401


def test_rota_protegida_com_token_valido_e_permitida(client, alice_headers):
    """Controle positivo: o mesmo pedido com token válido passa."""
    resp = client.get("/predictions", headers=alice_headers)

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
