"""População do banco SQLite com usuários e predictions de exemplo (sqlite3 puro).

É idempotente: usuários já cadastrados não são duplicados e as predictions de exemplo só
são inseridas quando o dono ainda não tem nenhuma.

Uso (a partir da pasta fastapi/):
    python sqlite_populate.py            # popula o database.db (cria o schema se faltar)
"""

import sqlite3
from datetime import UTC, datetime

from security.passwords import hash_password

# Credenciais acadêmicas (apenas para o trabalho).
SEED_USERS = [
    ("admin", "admin123"),  # usuário do TP1, mantido
    ("alice", "alice123"),
    ("bob", "bob123"),
]

# (username do dono, texto, intenção, confiança). As intenções são as cinco classes
# de `Ticket Type` formalizadas no TP3 (domain/prediction.py).
SEED_PREDICTIONS = [
    ("alice", "I need a refund for my last order", "refund_request", 0.91),
    ("alice", "My invoice has a wrong amount", "billing_inquiry", 0.84),
    ("bob", "The app crashes when I log in", "technical_issue", 0.88),
    ("bob", "How do I cancel my subscription?", "cancellation_request", 0.79),
    ("admin", "Is this camera compatible with my laptop?", "product_inquiry", 0.82),
]


def _now() -> str:
    # Formato aceito pelo SQLAlchemy/SQLModel para colunas DateTime no SQLite.
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def populate(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO users (username, hashed_password) VALUES (?, ?)",
        [(u, hash_password(p)) for u, p in SEED_USERS],
    )
    ids = {u: i for i, u in conn.execute("SELECT id, username FROM users")}
    owners_with_data = {
        owner for (owner,) in conn.execute("SELECT DISTINCT owner_id FROM predictions")
    }
    conn.executemany(
        "INSERT INTO predictions (owner_id, text, intent, confidence, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (ids[o], t, i, c, _now())
            for o, t, i, c in SEED_PREDICTIONS
            if ids[o] not in owners_with_data
        ],
    )
    conn.commit()


if __name__ == "__main__":
    from sqlite_database import DB_PATH, init_db

    init_db(DB_PATH)
    with sqlite3.connect(DB_PATH) as c:
        populate(c)
        n_u = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_p = c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    print(f"Banco populado em {DB_PATH} ({n_u} usuários, {n_p} predictions)")
