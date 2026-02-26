"""
Privacy utilities for the AI Job Agent.

Principles
──────────
1. PII (name, email, phone) is AES-256-GCM encrypted at rest.
2. The encryption key is derived from a user-supplied passphrase via PBKDF2-HMAC-SHA256.
3. No PII is ever logged or transmitted to the Anthropic API.
4. The agent only sends skill/role/location context to the model — never identifying details.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ── Key derivation ─────────────────────────────────────────────────────────

def derive_key(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Return (key, salt) from a user passphrase using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode(),
        salt,
        iterations=390_000,   # OWASP 2023 recommendation
        dklen=32,
    )
    return key, salt


# ── Encryption / decryption ────────────────────────────────────────────────

def encrypt(plaintext: str, key: bytes) -> str:
    """Encrypt plaintext → base64-encoded 'nonce||ciphertext' string."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    blob = nonce + ct
    return base64.b64encode(blob).decode()


def decrypt(ciphertext_b64: str, key: bytes) -> str:
    """Decrypt base64-encoded 'nonce||ciphertext' → plaintext string."""
    blob = base64.b64decode(ciphertext_b64.encode())
    nonce, ct = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()


# ── PII scrubbing ──────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(
    r"(\+?1?\s*[-.]?\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
)
# Very simple name heuristic: two+ capitalised words in a row
_NAME_RE = re.compile(r"\b([A-Z][a-z]+\s){1,3}[A-Z][a-z]+\b")


def scrub_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """Remove obvious PII from a string before sending it to any external API."""
    text = _EMAIL_RE.sub(replacement, text)
    text = _PHONE_RE.sub(replacement, text)
    text = _NAME_RE.sub(replacement, text)
    return text


def sanitise_for_llm(data: dict[str, Any]) -> dict[str, Any]:
    """
    Return a copy of *data* safe to pass to the language model.
    Strips or redacts fields that could contain PII.
    """
    SAFE_FIELDS = {
        "skills", "experience_level", "years_of_experience",
        "education", "desired_roles", "desired_job_types",
        "desired_salary_min", "desired_salary_max",
        "languages", "certifications",
        "location",          # city / region only — not address
    }
    return {k: v for k, v in data.items() if k in SAFE_FIELDS}


# ── Bias guard ─────────────────────────────────────────────────────────────

_PROTECTED = {
    "gender", "sex", "age", "race", "ethnicity", "religion",
    "nationality", "marital_status", "disability",
}


def strip_protected_attributes(profile_dict: dict[str, Any]) -> dict[str, Any]:
    """Remove any protected-attribute keys before scoring/recommending."""
    return {k: v for k, v in profile_dict.items() if k.lower() not in _PROTECTED}
