import pytest

from erc7730.convert.calldata.v1.enum import enum_ordinal


@pytest.mark.parametrize(
    "ordinal,expected",
    [
        pytest.param("0", 0, id="zero"),
        pytest.param("1", 1, id="one"),
        pytest.param("42", 42, id="larger"),
        pytest.param("-1", -1, id="negative"),
    ],
)
def test_a_decimal_key_is_its_own_value(ordinal: str, expected: int) -> None:
    assert enum_ordinal(ordinal) == expected


@pytest.mark.parametrize(
    "ordinal,expected",
    [
        pytest.param("false", 0, id="false"),
        pytest.param("true", 1, id="true"),
        pytest.param("False", 0, id="False"),
        pytest.param("True", 1, id="True"),
        pytest.param("FALSE", 0, id="FALSE"),
        pytest.param("TRUE", 1, id="TRUE"),
        pytest.param(" true ", 1, id="padded"),
    ],
)
def test_a_boolean_key_is_the_value_the_bool_holds_in_calldata(ordinal: str, expected: int) -> None:
    """A bool holds 0 or 1, and the casing follows whoever wrote the descriptor."""
    assert enum_ordinal(ordinal) == expected


@pytest.mark.parametrize("ordinal", ["maybe", "", "0x1", "1.0", "yes"])
def test_a_key_that_is_neither_still_raises(ordinal: str) -> None:
    """Silently mapping an unrecognised key to a number would build an entry that never matches."""
    with pytest.raises(ValueError):
        enum_ordinal(ordinal)
