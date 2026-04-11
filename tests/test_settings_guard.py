"""Tests for production configuration guard."""
from __future__ import annotations

import pytest


def test_production_without_auth_raises(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", False)
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="AUTH_ENABLED must be true"):
        validate_production_config()


def test_production_with_auth_ok(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.setenv("PII_ENCRYPTION_PASSPHRASE", "test-strong-passphrase-12345")
    from config.settings import validate_production_config
    validate_production_config()  # should not raise


def test_production_with_default_encryption_key_raises(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", True)
    monkeypatch.setattr("config.settings.DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.delenv("PII_ENCRYPTION_PASSPHRASE", raising=False)
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="PII_ENCRYPTION_PASSPHRASE"):
        validate_production_config()


def test_development_without_auth_ok(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "development")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", False)
    from config.settings import validate_production_config
    validate_production_config()  # should not raise


# ── P0.5 / P0.6: new staging + SQLite-fallthrough coverage ──────────────────


def test_staging_without_passphrase_raises(monkeypatch):
    """Staging must enforce the same PII passphrase rule as production."""
    monkeypatch.setattr("config.settings.ENV", "staging")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", True)
    monkeypatch.setattr("config.settings.DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.delenv("PII_ENCRYPTION_PASSPHRASE", raising=False)
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="PII_ENCRYPTION_PASSPHRASE"):
        validate_production_config()


def test_production_without_database_url_raises(monkeypatch):
    """Prod must refuse to fall through to local SQLite on ephemeral FS."""
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", False)  # isolate the DB check
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="DATABASE_URL must be set"):
        validate_production_config()


def test_production_with_sqlite_url_raises(monkeypatch):
    """A sqlite:// DATABASE_URL in prod is the same failure class as unset."""
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", False)
    monkeypatch.setattr("config.settings.DATABASE_URL", "sqlite:///data/job_agent.db")
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="DATABASE_URL must be set"):
        validate_production_config()


def test_staging_without_database_url_raises(monkeypatch):
    """Staging shares the prod DB guard."""
    monkeypatch.setattr("config.settings.ENV", "staging")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", False)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="DATABASE_URL must be set"):
        validate_production_config()
