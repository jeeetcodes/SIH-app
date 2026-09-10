"""SQLAlchemy engine, sessions, and table initialization.

Set ``DATABASE_URL`` to a PostgreSQL URL in production, for example:
``postgresql://label_police:password@localhost:5432/label_police``.
The SQLite default remains useful for local development and tests.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args: dict[str, bool] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models before create_all so every table is registered with Base.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
