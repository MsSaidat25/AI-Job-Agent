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
    monkeypatch.setenv("PII_ENCRYPTION_PASSPHRASE", "test-strong-passphrase-12345")
    from config.settings import validate_production_config
    validate_production_config()  # should not raise


def test_production_with_default_encryption_key_raises(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "production")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", True)
    monkeypatch.setattr("config.settings.ENCRYPT_USER_DATA", True)
    monkeypatch.delenv("PII_ENCRYPTION_PASSPHRASE", raising=False)
    from config.settings import validate_production_config
    with pytest.raises(SystemExit, match="PII_ENCRYPTION_PASSPHRASE"):
        validate_production_config()


def test_development_without_auth_ok(monkeypatch):
    monkeypatch.setattr("config.settings.ENV", "development")
    monkeypatch.setattr("config.settings.AUTH_ENABLED", False)
    from config.settings import validate_production_config
    validate_production_config()  # should not raise
