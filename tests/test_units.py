import pytest

from hak_saucerswap_plugin.utils.units import format_units, parse_units


def test_parse_units_whole():
    assert parse_units("10", 6) == "10000000"


def test_parse_units_fraction():
    assert parse_units("1.5", 8) == "150000000"


def test_parse_units_zero():
    assert parse_units("0.0", 6) == "0"


def test_parse_units_too_many_decimals():
    with pytest.raises(ValueError):
        parse_units("1.1234567", 6)


def test_parse_units_invalid():
    with pytest.raises(ValueError):
        parse_units("abc", 6)


def test_format_units_basic():
    assert format_units("150000000", 8) == "1.5"


def test_format_units_no_fraction():
    assert format_units("10000000", 6) == "10"


def test_format_units_zero_decimals():
    assert format_units("42", 0) == "42"


def test_round_trip():
    assert format_units(parse_units("123.456", 8), 8) == "123.456"
