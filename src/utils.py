"""Shared utility functions for the AI Job Agent."""
from __future__ import annotations

import json
from typing import Any


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from an LLM JSON response.

    Handles both ``json ... `` and plain `` ... `` patterns.
    Returns the inner text ready for json.loads().
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


def parse_json_response(text: str) -> dict[str, Any]:
    """Strip fences then parse JSON from an LLM response."""
    return json.loads(strip_json_fences(text))
