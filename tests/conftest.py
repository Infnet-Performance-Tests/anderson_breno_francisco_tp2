"""Fixtures da suíte de testes (pytest tests/ -v).

- Usam o app REAL (fastapi/main.py) com TestClient e um banco TEMPORÁRIO criado por
  sqlite_database.init_db(), então o fastapi/database.db versionado nunca é alterado.
- O rate limiter do SlowAPI guarda contadores em memória: ele é zerado antes de cada teste
  e antes de cada login de fixture, para que um teste não esgote o limite do seguinte.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fastapi"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, create_engine  # noqa: E402

import sqlite_database  # noqa: E402
from database import get_session  # noqa: E402
from main import app  # noqa: E402
from security.rate_limit import limiter  # noqa: E402

CREDENTIALS = {
    "admin": "admin123",
    "alice": "alice123",
    "bob": "bob123",
}


@pytest.fixture(scope="session")
def db_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "test.db"
    sqlite_database.init_db(path)
    return path


@pytest.fixture
def session(db_file):
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    with Session(engine) as s:
        yield s


@pytest.fixture(scope="session")
def client(db_file):
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    def override_get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()


def login(client, username, password):
    return client.post("/auth/token", data={"username": username, "password": password})


def _bearer(client, username):
    limiter.reset()
    resp = login(client, username, CREDENTIALS[username])
    assert resp.status_code == 200, f"login de {username} falhou: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return _bearer(client, "admin")


@pytest.fixture(scope="session")
def alice_headers(client):
    return _bearer(client, "alice")


@pytest.fixture(scope="session")
def bob_headers(client):
    return _bearer(client, "bob")
