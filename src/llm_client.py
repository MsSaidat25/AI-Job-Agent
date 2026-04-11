# Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com). All Rights Reserved.
# avien@aviensolutions.com
"""
LLM Client Factory with Vertex AI failover.

Provides:
  - get_llm_client()                  -- returns the primary Anthropic client
  - create_message_with_failover()    -- wraps messages.create() with auto-failover

Failover behaviour:
  OpenRouter (primary) --> Vertex AI (failover, safe-by-default)

Vertex AI is "safe by default": data sent through Vertex is NOT used for
model training, aligning with this project's privacy-first design.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import anthropic

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    USE_VERTEX_PRIMARY,
    USE_VERTEX_FAILOVER,
    VERTEX_LOCATION,
    VERTEX_MODEL,
    VERTEX_PROJECT,
)

logger = logging.getLogger(__name__)

_primary_client: Any | None = None
_primary_lock = threading.Lock()
_vertex_client = None
_vertex_lock = threading.Lock()


def get_llm_client() -> Any:
    """Return the cached primary LLM client.

    Primary can be OpenRouter/direct Anthropic or Vertex AI based on config.
    """
    global _primary_client
    if _primary_client is not None:
        return _primary_client
    with _primary_lock:
        if _primary_client is None:
            if USE_VERTEX_PRIMARY:
                _primary_client = _get_vertex_client()
            else:
                kwargs: dict[str, Any] = {"api_key": LLM_API_KEY}
                if LLM_BASE_URL:
                    kwargs["base_url"] = LLM_BASE_URL
                _primary_client = anthropic.Anthropic(**kwargs)
    return _primary_client


def _get_vertex_client() -> Any:
    """Lazy-init the Vertex AI client (uses ADC, no API key needed on GCP)."""
    global _vertex_client
    if _vertex_client is not None:
        return _vertex_client
    with _vertex_lock:
        if _vertex_client is None:
            from anthropic import AnthropicVertex
            _vertex_client = AnthropicVertex(
                project_id=VERTEX_PROJECT,
                region=VERTEX_LOCATION,
            )
    return _vertex_client


def _is_retryable(exc: Exception) -> bool:
    """Decide whether an LLM error should trigger Vertex failover."""
    if isinstance(exc, anthropic.APITimeoutError):
        return True
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return True
    # Model not available in region -- failover to alternative
    if isinstance(exc, anthropic.BadRequestError):
        msg = str(exc).lower()
        if "not servable" in msg or "not found" in msg or "not available" in msg:
            return True
    return False


def create_message_with_failover(
    client: Any,
    **kwargs: Any,
) -> Any:
    """Call messages.create(), failing over to Vertex AI on retryable errors.

    Accepts the same kwargs as anthropic.Anthropic.messages.create().
    """
    try:
        return client.messages.create(**kwargs)
    except Exception as exc:
        if not _is_retryable(exc):
            raise
        # Failover: Vertex primary -> OpenRouter, or OpenRouter primary -> Vertex
        if USE_VERTEX_PRIMARY and LLM_API_KEY:
            logger.warning(
                "Primary Vertex AI failed (%s), failing over to OpenRouter",
                type(exc).__name__,
            )
            fallback_kwargs: dict[str, Any] = {"api_key": LLM_API_KEY}
            if LLM_BASE_URL:
                fallback_kwargs["base_url"] = LLM_BASE_URL
            fallback_client = anthropic.Anthropic(**fallback_kwargs)
            return fallback_client.messages.create(**kwargs)
        if (not USE_VERTEX_PRIMARY) and USE_VERTEX_FAILOVER and VERTEX_PROJECT:
            logger.warning(
                "Primary LLM failed (%s), failing over to Vertex AI",
                type(exc).__name__,
            )
            vertex = _get_vertex_client()
            vertex_kwargs = dict(kwargs)
            vertex_kwargs["model"] = VERTEX_MODEL
            return vertex.messages.create(**vertex_kwargs)
        raise
