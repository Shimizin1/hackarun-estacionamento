"""
Database configuration and session management.
SQLite with SQLAlchemy 2.0 async support.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool


# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "capimparking.db"
# Permite apontar para outro banco (testes, Postman/Newman) sem tocar em data/.
DATABASE_URL = os.getenv("CAPIM_DB_URL", f"sqlite:///{DB_PATH}")
_IN_MEMORY = DATABASE_URL in ("sqlite://", "sqlite:///:memory:")


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Engine configuration for SQLite
# StaticPool (conexão única) só para banco em memória; arquivo usa o pool padrão.
_engine_kwargs = {"connect_args": {"check_same_thread": False}, "echo": False}
if _IN_MEMORY:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Session:
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database: create all tables."""
    from app.models import Base  # noqa: F401
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables (for testing/reset)."""
    from app.models import Base  # noqa: F401
    Base.metadata.drop_all(bind=engine)


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan handler."""
    init_db()
    yield
    # Cleanup if needed