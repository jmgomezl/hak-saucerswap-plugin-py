from __future__ import annotations

from typing import Any


def _read_amount(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def normalize_swap_quote(quote: dict[str, Any], fallback_amount_in: str) -> dict[str, Any]:
    """Normalize a raw API quote into a stable shape.

    Returns a dict with: amount_in, expected_output, price_impact, route, raw.
    """
    amount_in = _read_amount(quote.get("amountIn")) or fallback_amount_in
    expected_output = (
        _read_amount(quote.get("expectedOutput"))
        or _read_amount(quote.get("amountOut"))
        or _read_amount(quote.get("amountOutMin"))
        or ""
    )
    if not expected_output:
        raise ValueError("SaucerSwap quote did not include an output amount.")

    price_impact = quote.get("priceImpact")
    route = quote.get("route")
    return {
        "amount_in": amount_in,
        "expected_output": expected_output,
        "price_impact": price_impact if isinstance(price_impact, (int, float)) else None,
        "route": route if isinstance(route, list) else [],
        "raw": quote,
    }
