from __future__ import annotations


def calculate_price_impact(
    input_amount: str,
    output_amount: str,
    pool_reserve_in: str,
    pool_reserve_out: str,
) -> float | None:
    """Estimate price impact (%) from constant-product pool reserves."""
    try:
        in_amount = float(input_amount)
        out_amount = float(output_amount)
        reserve_in = float(pool_reserve_in)
        reserve_out = float(pool_reserve_out)
    except (TypeError, ValueError):
        return None
    if min(in_amount, out_amount, reserve_in, reserve_out) <= 0:
        return None
    expected_output = (in_amount * reserve_out) / (reserve_in + in_amount)
    if expected_output <= 0:
        return None
    return (expected_output - out_amount) / expected_output * 100


def apply_slippage_to_amount(amount: str, slippage_tolerance: float) -> str:
    """Reduce a base-unit integer amount by the slippage tolerance percentage."""
    amount_int = int(amount)
    bps = max(0, round(slippage_tolerance * 100))
    return str(amount_int * (10_000 - bps) // 10_000)
