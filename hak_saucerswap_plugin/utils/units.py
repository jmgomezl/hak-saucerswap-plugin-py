"""Decimal <-> base-unit conversions using exact integer arithmetic."""

from __future__ import annotations

import re

DECIMAL_RE = re.compile(r"^\d+(\.\d+)?$")
INTEGER_RE = re.compile(r"^\d+$")


def parse_units(amount: str, decimals: int) -> str:
    """Convert a decimal amount string to a base-unit integer string."""
    if not amount or not isinstance(amount, str):
        raise ValueError("Amount must be a non-empty string.")
    if decimals < 0:
        raise ValueError("Decimals must be non-negative.")
    trimmed = amount.strip()
    if not DECIMAL_RE.match(trimmed):
        raise ValueError(f"Invalid amount format: {amount}")
    whole, _, fraction = trimmed.partition(".")
    if len(fraction) > decimals:
        raise ValueError(f"Amount has more than {decimals} decimal places.")
    combined = (whole + fraction.ljust(decimals, "0")).lstrip("0")
    return combined or "0"


def format_units(amount: str, decimals: int) -> str:
    """Convert a base-unit integer string to a decimal amount string."""
    if not amount or not isinstance(amount, str):
        raise ValueError("Amount must be a non-empty string.")
    if decimals < 0:
        raise ValueError("Decimals must be non-negative.")
    trimmed = amount.strip()
    if not INTEGER_RE.match(trimmed):
        raise ValueError(f"Invalid integer amount: {amount}")
    padded = trimmed.rjust(decimals + 1, "0")
    whole = padded[:-decimals] if decimals else padded
    fraction = padded[-decimals:].rstrip("0") if decimals else ""
    return f"{whole}.{fraction}" if fraction else whole
