"""
Fixtures do pytest.

IMPORTANTE: CAPIM_DB_URL precisa ser definida ANTES de importar `app`, para que
os testes nunca toquem em data/capimparking.db.
"""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="capim_tests_"))
_DB_FILE = _TMP / "test.db"
os.environ["CAPIM_DB_URL"] = f"sqlite:///{_DB_FILE.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, drop_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.config_service import ConfigService  # noqa: E402


@pytest.fixture
def client():
    """TestClient com banco NOVO (seed determinístico) a cada teste."""
    drop_db()
    ConfigService.invalidate_cache()
    with TestClient(app) as c:  # o lifespan cria as tabelas e roda o seed
        yield c
    ConfigService.invalidate_cache()


@pytest.fixture
def db(client):
    """Sessão direta no mesmo banco do `client`."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
