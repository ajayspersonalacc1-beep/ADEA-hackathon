"""Shared helper functions."""

from __future__ import annotations


def generate_placeholder_id(prefix: str = "adea") -> str:
    """Return a deterministic placeholder identifier."""

    return f"{prefix}-placeholder"


def format_stage_log(tag: str, message: str) -> str:
    """Return a consistently tagged execution log message."""

    normalized_tag = tag.strip().upper() or "ADEA"
    return f"[{normalized_tag}] {message}"
