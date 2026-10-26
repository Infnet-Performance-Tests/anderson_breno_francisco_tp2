"""Criação e população inicial do banco SQLite (usa sqlite3 puro, conforme o enunciado).

A população em si fica em sqlite_populate.py; este módulo cria o schema e, quando o banco
ainda está vazio, chama a população inicial.

Uso (a partir da pasta fastapi/):
    python sqlite_database.py            # cria e popula se ainda estiver vazio
    python sqlite_database.py --reset    # apaga o database.db e recria do zero
"""

import sqlite3
import sys
from pathlib import Path

from sqlite_populate import populate

DB_PATH = Path(__file__).resolve().parent / "database.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users (id),
    text VARCHAR NOT NULL,
    intent VARCHAR NOT NULL,
    confidence FLOAT NOT NULL,
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_predictions_owner_id ON predictions (owner_id);
"""


def init_db(db_path: Path | str = DB_PATH, reset: bool = False) -> Path:
    db_path = Path(db_path)
    if reset and db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            populate(conn)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = init_db(reset="--reset" in sys.argv)
    with sqlite3.connect(path) as c:
        n_u = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_p = c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    print(f"Banco pronto em {path} ({n_u} usuários, {n_p} predictions)")
