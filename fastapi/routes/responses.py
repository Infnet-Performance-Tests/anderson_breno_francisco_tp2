"""Respostas de erro reutilizadas na documentação OpenAPI das rotas protegidas."""

from fastapi import status

from models.responses import ErrorResponse

UNAUTHORIZED = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Token ausente, inválido, expirado ou de usuário inativo.",
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
    }
}

NOT_FOUND = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": (
            "A prediction não existe **ou** pertence a outro usuário. As duas situações têm a "
            "mesma resposta para não permitir enumerar IDs (proteção BOLA)."
        ),
        "content": {"application/json": {"example": {"detail": "Prediction not found"}}},
    }
}
