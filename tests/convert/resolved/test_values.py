import pytest

from erc7730.common.abi import ABIDataType
from erc7730.common.output import RaisingOutputAdder
from erc7730.convert.resolved.values import encode_value
from erc7730.model.types import HexStr, ScalarType


@pytest.mark.parametrize(
    "abi_type,value,expected",
    [
        (ABIDataType.UINT, "0xaaa", "0xaaa"),
        (ABIDataType.INT, "0xaaa", "0xaaa"),
        (ABIDataType.UFIXED, "0xaaa", "0xaaa"),
        (ABIDataType.FIXED, "0xaaa", "0xaaa"),
        (ABIDataType.ADDRESS, "0xaaa", "0xaaa"),
        (ABIDataType.BOOL, "0xaaa", "0xaaa"),
        (ABIDataType.BYTES, "0xaaa", "0xaaa"),
        (ABIDataType.STRING, "0xaaa", "0xaaa"),
        (ABIDataType.UINT, 42, "0x000000000000000000000000000000000000000000000000000000000000002a"),
        (ABIDataType.INT, 42, "0x000000000000000000000000000000000000000000000000000000000000002a"),
        (ABIDataType.INT, -42, "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd6"),
        (ABIDataType.UFIXED, 42, "0x00000000000000000000000000000000000000000000000246ddf97976680000"),
        (ABIDataType.FIXED, 42, "0x00000000000000000000000000000000000000000000000246ddf97976680000"),
        (ABIDataType.FIXED, -42, "0xfffffffffffffffffffffffffffffffffffffffffffffffdb922068689980000"),
        (ABIDataType.BOOL, True, "0x0000000000000000000000000000000000000000000000000000000000000001"),
        (ABIDataType.BOOL, False, "0x0000000000000000000000000000000000000000000000000000000000000000"),
        (ABIDataType.BYTES, "0xcafebabe", "0xcafebabe"),
        (
            ABIDataType.BYTES,
            "0xcafebabecafebabecafebabecafebabecafebabecafebabe",
            "0xcafebabecafebabecafebabecafebabecafebabecafebabe",
        ),
        (
            ABIDataType.ADDRESS,
            "0x11111112542D85B3EF69AE05771c2dCCff4fAa26",
            "0x11111112542d85b3ef69ae05771c2dccff4faa26",
        ),
        (
            ABIDataType.STRING,
            "hi",
            "0x"
            "0000000000000000000000000000000000000000000000000000000000000002"
            "6869000000000000000000000000000000000000000000000000000000000000",
        ),
        (
            ABIDataType.STRING,
            "hi this is a very long string, because we want to test what happens with several chunks",
            "0x"
            "0000000000000000000000000000000000000000000000000000000000000057"
            "6869207468697320697320612076657279206c6f6e6720737472696e672c2062"
            "6563617573652077652077616e7420746f207465737420776861742068617070"
            "656e732077697468207365766572616c206368756e6b73000000000000000000",
        ),
    ],
)
def test_encode_value(abi_type: ABIDataType, value: ScalarType, expected: HexStr) -> None:
    assert encode_value(value, abi_type, RaisingOutputAdder()) == expected


@pytest.mark.parametrize(
    "abi_type,value,expected",
    [
        (ABIDataType.UINT, -42, """Value "-42" is not a uint"""),
        (ABIDataType.UINT, "42", """Value "42" is not a uint"""),
        (ABIDataType.ADDRESS, "42", """Value "42" is not a address"""),
        (ABIDataType.BOOL, "42", """Value "42" is not a bool"""),
        (ABIDataType.BYTES, "42", """Value "42" is not a bytes"""),
        (ABIDataType.STRING, 42, """Value "42" is not a string"""),
    ],
)
def test_encode_value_error(abi_type: ABIDataType, value: ScalarType, expected: str) -> None:
    with pytest.raises(Exception) as exc_info:
        encode_value(value, abi_type, RaisingOutputAdder())
    assert expected in str(exc_info.value)
