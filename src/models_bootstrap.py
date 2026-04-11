"""Database bootstrap: engine creation, migrations, and session factory."""
from __future__ import annotations

import logging
import threading

from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL, DATABASE_URL_FAILOVER, DB_PATH
from src.models_db import Base

logger = logging.getLogger(__name__)

_active_engine = None
_init_lock = threading.RLock()
_tables_created = False
_SessionFactory: sessionmaker | None = None


def reset_db_state() -> None:
    """Reset cached engine and session factory. Used by tests for isolation."""
    global _active_engine, _tables_created, _SessionFactory
    with _init_lock:
        _active_engine = None
        _tables_created = False
        _SessionFactory = None


def get_active_engine():  # type: ignore[no-untyped-def]
    """Return the currently cached engine, or None if not yet initialised."""
    return _active_engine


def _enable_sqlite_fk(dbapi_conn, connection_record):  # type: ignore[no-untyped-def]
    """Enable foreign key enforcement for SQLite connections."""
    import sqlite3
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def get_engine(failover: bool = False):  # type: ignore[no-untyped-def]
    """Return a cached SQLAlchemy engine, creating one if needed."""
    global _active_engine
    if _active_engine is not None and not failover:
        return _active_engine
    with _init_lock:
        if _active_engine is not None and not failover:
            return _active_engine
        url = DATABASE_URL_FAILOVER if failover else DATABASE_URL
        if failover and not DATABASE_URL_FAILOVER:
            logger.error(
                "Failover requested but DATABASE_URL_FAILOVER is not configured; "
                "refusing to silently fall back to SQLite."
            )
            raise ValueError("DATABASE_URL_FAILOVER must be set when failover=True is requested")
        if url:
            engine = create_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True, echo=False)
        else:
            from sqlalchemy import event
            engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
            event.listen(engine, "connect", _enable_sqlite_fk)
        _active_engine = engine
        return engine


def _run_migrations(engine) -> None:  # type: ignore[no-untyped-def]
    """Run Alembic migrations to HEAD, falling back to create_all for fresh DBs."""
    try:
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config("alembic.ini")
        with engine.begin() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception:
        logger.warning("Alembic migration failed, falling back to create_all", exc_info=True)
        Base.metadata.create_all(engine)
        try:
            from alembic import command
            from alembic.config import Config
            alembic_cfg = Config("alembic.ini")
            command.stamp(alembic_cfg, "head")
            logger.info("Stamped database at Alembic HEAD after create_all fallback")
        except Exception:
            logger.warning("Could not stamp Alembic HEAD", exc_info=True)


def init_db() -> Session:
    """Initialise the database, with automatic failover on connection error."""
    global _active_engine, _tables_created, _SessionFactory
    from sqlalchemy import text

    with _init_lock:
        for attempt_failover in (False, True):
            try:
                engine = get_engine(failover=attempt_failover)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                if not _tables_created:
                    _run_migrations(engine)
                    _tables_created = True
                if _SessionFactory is None or _SessionFactory.kw.get("bind") is not engine:
                    _SessionFactory = sessionmaker(bind=engine)
                if attempt_failover:
                    logger.warning("Using failover database")
                return _SessionFactory()
            except (OperationalError, DBAPIError) as exc:
                if not attempt_failover and DATABASE_URL_FAILOVER:
                    logger.warning("Primary database unreachable, trying failover: %s", exc)
                    _active_engine = None
                    _tables_created = False
                    _SessionFactory = None
                    continue
                raise
    raise RuntimeError("Database initialisation failed")
