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
        (ABIDataType.UINT, 42, "0x2a"),
        (ABIDataType.INT, 42, "0x2a"),
        (ABIDataType.INT, -42, "0xd6"),
        (ABIDataType.BOOL, True, "0x01"),
        (ABIDataType.BOOL, False, "0x00"),
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
        (ABIDataType.STRING, "hi", "0x6869"),
        (
            ABIDataType.STRING,
            "hi this is a very long string, because we want to test what happens with several chunks",
            "0x6869207468697320697320612076657279206c6f6e6720737472696e672c20626563617573652077652077616e7420746f20746"
            "5737420776861742068617070656e732077697468207365766572616c206368756e6b73",
        ),
    ],
)
def test_encode_value(abi_type: ABIDataType, value: ScalarType, expected: HexStr) -> None:
    assert encode_value(value, abi_type, RaisingOutputAdder()) == expected


@pytest.mark.parametrize(
    "abi_type,value,expected",
    [
        (ABIDataType.UINT, -42, """Value "-42" is not an unsigned int"""),
        (ABIDataType.UINT, "42", """Value "42" is not an unsigned int"""),
        (ABIDataType.ADDRESS, "42", """Value "42" is not a valid address hexadecimal string"""),
        (ABIDataType.BOOL, "42", """Value "42" is not a bool"""),
        (ABIDataType.BYTES, "42", """Value "42" is not a valid hexadecimal string"""),
        (ABIDataType.STRING, 42, """Value "42" is not a string"""),
        (ABIDataType.FIXED, 42, """Fixed precision numbers are not supported"""),
        (ABIDataType.UFIXED, 42, """Fixed precision numbers are not supported"""),
    ],
)
def test_encode_value_error(abi_type: ABIDataType, value: ScalarType, expected: str) -> None:
    with pytest.raises(Exception) as exc_info:
        encode_value(value, abi_type, RaisingOutputAdder())
    assert expected in str(exc_info.value)
