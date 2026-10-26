"""Segurança — autorização/BOLA: um usuário autenticado não acessa recursos de outro.

Parte 1: camada de dados - a consulta com ownership não devolve recurso alheio.
Parte 2: camada HTTP - GET /predictions e GET /predictions/{id} respeitam o dono.
"""

from sqlmodel import select

import crud
from models.tables import User


def _user(session, username):
    return session.exec(select(User).where(User.username == username)).one()


# ---------- camada de dados ----------
def test_consulta_com_ownership_nao_retorna_recurso_de_outro_usuario(session):
    alice, bob = _user(session, "alice"), _user(session, "bob")
    alice_prediction = crud.list_predictions_by_owner(session, alice.id)[0]

    assert crud.get_prediction_for_owner(session, alice_prediction.id, alice.id) is not None
    assert crud.get_prediction_for_owner(session, alice_prediction.id, bob.id) is None


def test_listagem_por_dono_nao_mistura_usuarios(session):
    alice, bob = _user(session, "alice"), _user(session, "bob")
    alice_ids = {p.id for p in crud.list_predictions_by_owner(session, alice.id)}
    bob_ids = {p.id for p in crud.list_predictions_by_owner(session, bob.id)}

    assert alice_ids and bob_ids
    assert alice_ids.isdisjoint(bob_ids)


# ---------- camada HTTP ----------
def test_usuario_nao_acessa_prediction_de_outro_usuario(client, alice_headers, bob_headers):
    alice_prediction = client.get("/predictions", headers=alice_headers).json()[0]

    own = client.get(f"/predictions/{alice_prediction['id']}", headers=alice_headers)
    assert own.status_code == 200  # controle positivo: o dono acessa
    assert own.json()["text"] == alice_prediction["text"]

    other = client.get(f"/predictions/{alice_prediction['id']}", headers=bob_headers)
    assert other.status_code == 404
    assert other.json() == {"detail": "Prediction not found"}
    assert alice_prediction["text"] not in other.text


def test_id_de_outro_usuario_e_id_inexistente_tem_mesma_resposta(
    client, alice_headers, bob_headers
):
    """Não deve ser possível enumerar quais ids existem."""
    alice_id = client.get("/predictions", headers=alice_headers).json()[0]["id"]
    de_outro = client.get(f"/predictions/{alice_id}", headers=bob_headers)
    inexistente = client.get("/predictions/999999", headers=bob_headers)

    assert de_outro.status_code == inexistente.status_code == 404
    assert de_outro.json() == inexistente.json()


def test_listagem_http_so_traz_recursos_do_proprio_usuario(client, alice_headers, bob_headers):
    alice_ids = {p["id"] for p in client.get("/predictions", headers=alice_headers).json()}
    bob_ids = {p["id"] for p in client.get("/predictions", headers=bob_headers).json()}

    assert alice_ids and bob_ids
    assert alice_ids.isdisjoint(bob_ids)


def test_prediction_criada_pertence_a_quem_a_criou(client, alice_headers, bob_headers):
    created = client.post(
        "/predict", json={"text": "My card was charged twice"}, headers=bob_headers
    )
    assert created.status_code == 200
    new_id = created.json()["id"]

    assert client.get(f"/predictions/{new_id}", headers=bob_headers).status_code == 200
    assert client.get(f"/predictions/{new_id}", headers=alice_headers).status_code == 404
