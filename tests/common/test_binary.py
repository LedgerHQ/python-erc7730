from enum import IntEnum

import pytest

from erc7730.common.binary import tlv


class _Tag(IntEnum):
    FIELD = 5


@pytest.mark.parametrize(
    "tag, value, expected",
    [
        (1, None, b"\x01\x00"),
        (1, b"\xab", b"\x01\x01\xab"),
        (1, "hi", b"\x01\x02hi"),
        (_Tag.FIELD, b"\xff", b"\x05\x01\xff"),
        (0x80, None, b"\x81\x80\x00"),
        (1, b"\x00" * 128, b"\x01\x81\x80" + b"\x00" * 128),
    ],
)
def test_tlv(tag: int | IntEnum, value: bytes | str | None, expected: bytes) -> None:
    assert tlv(tag, value) == expected


@pytest.mark.parametrize(
    "tag, value, exc",
    [
        (256, None, OverflowError),
        (1, b"\x00" * 256, OverflowError),
        (1, "là-haut", UnicodeEncodeError),
    ],
)
def test_tlv_errors(tag: int, value: bytes | str | None, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        tlv(tag, value)
