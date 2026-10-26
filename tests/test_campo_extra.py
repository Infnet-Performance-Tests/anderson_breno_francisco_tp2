"""Segurança — validação de entrada: Pydantic rejeita campos extras e valores inválidos."""

import pytest

from models.prediction import PredictionRequest
from models.requests import StrictRequest


def test_campo_extra_no_body_e_rejeitado(client, admin_headers):
    resp = client.post(
        "/predict",
        json={"text": "I need help with a refund", "owner_id": 1, "is_admin": True},
        headers=admin_headers,
    )

    assert resp.status_code == 422
    rejeitados = {e["loc"][-1] for e in resp.json()["detail"] if e["type"] == "extra_forbidden"}
    assert {"owner_id", "is_admin"} <= rejeitados


@pytest.mark.parametrize(
    ("body", "erro"),
    [
        ({"text": "   "}, "string_too_short"),
        ({"text": "x" * 5_001}, "string_too_long"),
        ({"text": 123}, "string_type"),
        ({}, "missing"),
    ],
    ids=["texto-em-branco", "texto-longo-demais", "tipo-errado", "campo-ausente"],
)
def test_body_invalido_e_rejeitado(client, admin_headers, body, erro):
    resp = client.post("/predict", json=body, headers=admin_headers)

    assert resp.status_code == 422
    assert erro in {e["type"] for e in resp.json()["detail"]}


@pytest.mark.parametrize("prediction_id", ["abc", "0", "-1", "1 OR 1=1"])
def test_id_invalido_na_rota_e_rejeitado(client, alice_headers, prediction_id):
    resp = client.get(f"/predictions/{prediction_id}", headers=alice_headers)

    assert resp.status_code == 422


def test_json_malformado_e_rejeitado(client, admin_headers):
    resp = client.post(
        "/predict",
        content=b'{"text": "abc"',
        headers={**admin_headers, "Content-Type": "application/json"},
    )

    assert resp.status_code == 422


def test_body_valido_continua_funcionando(client, admin_headers):
    """Controle positivo: sem campo extra, a request passa."""
    resp = client.post(
        "/predict", json={"text": "I need help with a refund"}, headers=admin_headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"id", "intent", "confidence", "model_version"}
    assert body["model_version"] == "stub-v0"


def test_modelo_de_request_herda_da_base_estrita():
    assert issubclass(PredictionRequest, StrictRequest)
    assert PredictionRequest.model_config["extra"] == "forbid"
