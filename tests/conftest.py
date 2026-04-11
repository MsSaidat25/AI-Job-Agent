"""Shared test fixtures."""
import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Provide an isolated SQLite DB for tests that touch the database layer.

    Monkeypatches DB_PATH and DATABASE_URL in both config.settings and src.models,
    resets cached engine/session factory, creates all tables, and returns the path.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    from src.models import reset_db_state
    reset_db_state()
    return db_path
