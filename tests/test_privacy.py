"""Tests for privacy utilities."""
import pytest
from src.privacy import (
    decrypt,
    derive_key,
    encrypt,
    sanitise_for_llm,
    scrub_pii,
    strip_protected_attributes,
)


def test_derive_key_deterministic():
    key1, salt = derive_key("mysecret")
    key2, _ = derive_key("mysecret", salt)
    assert key1 == key2


def test_derive_key_different_salts():
    key1, _ = derive_key("mysecret")
    key2, _ = derive_key("mysecret")
    # Different random salts → different keys
    assert key1 != key2


def test_encrypt_decrypt_roundtrip():
    key, _ = derive_key("testpassphrase")
    plaintext = "alice@example.com"
    ciphertext = encrypt(plaintext, key)
    assert ciphertext != plaintext
    recovered = decrypt(ciphertext, key)
    assert recovered == plaintext


def test_scrub_pii_email():
    result = scrub_pii("Contact me at alice@example.com for details.")
    assert "alice@example.com" not in result
    assert "[REDACTED]" in result


def test_scrub_pii_phone():
    result = scrub_pii("Call me at 555-867-5309.")
    assert "867-5309" not in result


def test_sanitise_for_llm_removes_pii_fields():
    profile = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "skills": ["Python", "SQL"],
        "location": "Austin, TX",
    }
    safe = sanitise_for_llm(profile)
    assert "name" not in safe
    assert "email" not in safe
    assert "skills" in safe
    assert "location" in safe


def test_strip_protected_attributes():
    data = {
        "skills": ["Python"],
        "gender": "female",
        "age": 30,
        "ethnicity": "Hispanic",
    }
    clean = strip_protected_attributes(data)
    assert "gender" not in clean
    assert "age" not in clean
    assert "ethnicity" not in clean
    assert "skills" in clean
