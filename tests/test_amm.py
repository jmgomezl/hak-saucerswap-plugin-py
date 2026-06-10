from hak_saucerswap_plugin.utils.amm import apply_slippage_to_amount, calculate_price_impact


def test_apply_slippage():
    assert apply_slippage_to_amount("10000", 0.5) == "9950"


def test_apply_slippage_zero():
    assert apply_slippage_to_amount("10000", 0) == "10000"


def test_apply_slippage_negative_clamped():
    assert apply_slippage_to_amount("10000", -5) == "10000"


def test_price_impact_positive():
    impact = calculate_price_impact("100", "90", "10000", "10000")
    assert impact is not None
    assert impact > 0


def test_price_impact_invalid_inputs():
    assert calculate_price_impact("0", "90", "10000", "10000") is None
    assert calculate_price_impact("abc", "90", "10000", "10000") is None
