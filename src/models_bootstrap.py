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
    """Bring the database schema up to HEAD, safely.

    Three paths:

    1. **Fresh database** — no ``alembic_version`` table. Bootstrap via
       ``Base.metadata.create_all()`` and stamp HEAD. This is the first-run
       path for local dev, tests, and brand-new prod deploys. We explicitly
       do NOT call ``alembic upgrade head`` on fresh DBs because our initial
       migration is a diff, not a baseline, and will fail against an empty
       schema.

    2. **Orphaned bootstrap** — ``alembic_version`` table exists but is empty.
       This happens when a previous stamp transaction was rolled back, when
       somebody ran ``alembic stamp base`` by hand, or when a row was deleted.
       If every ORM-declared table already exists in the DB, the schema is
       identical to HEAD and we just insert the missing version row. If any
       ORM table is missing, the schema is mixed — fail loud so the operator
       can investigate.

    3. **Existing database** — ``alembic_version`` has a row. Run
       ``alembic upgrade head``. If that fails, re-raise loudly: a silent
       ``create_all`` fallback here would mask real schema drift (the exact
       bug P0 was opened to fix).
    """
    from sqlalchemy import inspect, text
    from alembic import command
    from alembic.config import Config

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    alembic_cfg = Config("alembic.ini")

    if "alembic_version" not in existing_tables:
        logger.info(
            "Fresh database detected (no alembic_version table); "
            "bootstrapping via create_all + stamp HEAD"
        )
        Base.metadata.create_all(engine)
        try:
            with engine.begin() as conn:
                alembic_cfg.attributes["connection"] = conn
                command.stamp(alembic_cfg, "head")
        except Exception:
            logger.error(
                "Failed to stamp Alembic HEAD on fresh-DB bootstrap. "
                "Next migration run will likely fail. Investigate immediately.",
                exc_info=True,
            )
            raise
        logger.info("Fresh database bootstrapped and stamped at HEAD")
        return

    # alembic_version table exists — check whether a row is recorded.
    with engine.connect() as conn:
        current_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    if current_rev is None:
        # Orphaned bootstrap: schema may already be at HEAD, just missing the row.
        orm_tables = set(Base.metadata.tables.keys())
        missing = orm_tables - existing_tables
        if missing:
            logger.error(
                "alembic_version table is empty AND ORM tables are missing (%s). "
                "This is a mixed schema state. Refusing to auto-recover. "
                "Either stamp the correct revision manually or rebuild the database.",
                sorted(missing),
            )
            raise RuntimeError(
                "Orphaned alembic_version with missing ORM tables; manual recovery required"
            )
        logger.warning(
            "alembic_version table exists but is empty and ORM schema matches HEAD; "
            "stamping HEAD to repair the orphaned bootstrap state."
        )
        try:
            with engine.begin() as conn:
                alembic_cfg.attributes["connection"] = conn
                command.stamp(alembic_cfg, "head")
            logger.info("Orphaned alembic_version stamped at HEAD")
        except Exception:
            logger.error(
                "Failed to stamp HEAD on orphaned alembic_version recovery.",
                exc_info=True,
            )
            raise
        return

    # Existing database with a real version row: run the real migration path.
    try:
        with engine.begin() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied to HEAD")
    except Exception:
        logger.error(
            "Alembic migration failed against a database that already has "
            "alembic_version (tables=%d). Refusing to silently fall back to "
            "create_all — investigate schema drift.",
            len(existing_tables),
        )
        raise


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
