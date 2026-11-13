"""
Database configuration and session management.
SQLite with SQLAlchemy 2.0 async support.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool


# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "capimparking.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Engine configuration for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,  # Set to True for SQL debugging
)


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