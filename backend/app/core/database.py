"""Backward-compatible imports for the canonical database module."""

from app.db.database import Base, SessionLocal, engine, get_db, init_db

__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_db"]
