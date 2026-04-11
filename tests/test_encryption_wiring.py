"""Tests for ENCRYPT_USER_DATA wiring through the ORM layer."""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import pytest

from src.models import (
    UserProfile,
    profile_to_orm,
    orm_to_profile,
    reset_encryption_key,
)


@pytest.fixture(autouse=True)
def _reset_key():
    reset_encryption_key()
    yield
    reset_encryption_key()


def _sample_profile() -> UserProfile:
    return UserProfile(
        name="Alice Smith",
        email="alice@example.com",
        phone="+1-555-123-4567",
        location="Austin, TX",
        skills=["Python", "SQL"],
        desired_roles=["Data Engineer"],
    )


class TestEncryptionEnabled:
    def test_pii_encrypted_in_orm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", True)
        profile = _sample_profile()
        orm = profile_to_orm(profile)

        # Encrypted values should NOT be plaintext
        name_val: str = orm.name_enc  # type: ignore[assignment]
        email_val: str = orm.email_enc  # type: ignore[assignment]
        phone_val: str = orm.phone_enc  # type: ignore[assignment]
        assert name_val != "Alice Smith"
        assert email_val != "alice@example.com"
        assert phone_val != "+1-555-123-4567"

        # Non-PII should be plaintext
        assert orm.location == "Austin, TX"

    def test_roundtrip_preserves_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", True)
        profile = _sample_profile()
        orm = profile_to_orm(profile)
        recovered = orm_to_profile(orm)

        assert recovered.name == "Alice Smith"
        assert recovered.email == "alice@example.com"
        assert recovered.phone == "+1-555-123-4567"
        assert recovered.location == "Austin, TX"
        assert recovered.skills == ["Python", "SQL"]

    def test_null_phone_handled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", True)
        profile = _sample_profile()
        profile.phone = None
        orm = profile_to_orm(profile)
        assert orm.phone_enc is None
        recovered = orm_to_profile(orm)
        assert recovered.phone is None


class TestEncryptionDisabled:
    def test_pii_stored_plaintext(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", False)
        profile = _sample_profile()
        orm = profile_to_orm(profile)

        name_val: str = orm.name_enc  # type: ignore[assignment]
        email_val: str = orm.email_enc  # type: ignore[assignment]
        phone_val: str = orm.phone_enc  # type: ignore[assignment]
        assert name_val == "Alice Smith"
        assert email_val == "alice@example.com"
        assert phone_val == "+1-555-123-4567"

    def test_roundtrip_plaintext(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.models_db.ENCRYPT_USER_DATA", False)
        profile = _sample_profile()
        orm = profile_to_orm(profile)
        recovered = orm_to_profile(orm)

        assert recovered.name == "Alice Smith"
        assert recovered.email == "alice@example.com"
