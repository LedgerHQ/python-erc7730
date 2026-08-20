from enum import IntEnum

import pytest

from erc7730.common.binary import der_encode_int, encode_fixed, length_value, tlv


class _Tag(IntEnum):
    FIELD = 5


@pytest.mark.parametrize(
    "tag, value, expected",
    [
        (1, None, b"\x01\x00"),
        (1, b"\xab", b"\x01\x01\xab"),
        (1, bytearray(b"\xab"), b"\x01\x01\xab"),
        (1, "hi", b"\x01\x02hi"),
        (_Tag.FIELD, b"\xff", b"\x05\x01\xff"),
        (0x80, None, b"\x81\x80\x00"),
        (1, b"\x00" * 128, b"\x01\x81\x80" + b"\x00" * 128),
        # DER long-form tag / length beyond 255
        (256, None, b"\x82\x01\x00\x00"),
        (1, b"\x00" * 256, b"\x01\x82\x01\x00" + b"\x00" * 256),
    ],
)
def test_tlv(tag: int | IntEnum, value: bytes | str | None, expected: bytes) -> None:
    assert tlv(tag, value) == expected


def test_tlv_encode_error() -> None:
    with pytest.raises(UnicodeEncodeError):
        tlv(1, "là-haut")


@pytest.mark.parametrize(
    "input,expected",
    [
        (None, b"\x00"),
        (b"", b"\x00"),
        ("", b"\x00"),
        (b"FOO", b"\x03FOO"),
        ("FOO", b"\x03FOO"),
        (b"a" * 255, b"\x81\xff" + b"a" * 255),
        (0, b"\x01\x00"),
        (123, b"\x01\x7b"),
        (123456789, b"\x04\x07\x5b\xcd\x15"),
        (12345678901234567890, b"\x08\xab\x54\xa9\x8c\xeb\x1f\x0a\xd2"),
    ],
)
def test_length_value_der_encoded_length(input: bytes | str | int | None, expected: bytes) -> None:
    assert length_value(input, der_encode_length=True) == expected


def test_length_value_overflow() -> None:
    with pytest.raises(OverflowError):
        length_value(b"a" * 256)


def test_length_value_max_length_error() -> None:
    with pytest.raises(OverflowError):
        length_value("a" * 50, max_length=10)


def test_length_value_encode_error() -> None:
    with pytest.raises(UnicodeEncodeError):
        length_value("😈")


@pytest.mark.parametrize(
    "input,expected",
    [
        (1, b"\x01"),
        (255, b"\x81\xff"),
        (65535, b"\x82\xff\xff"),
    ],
)
def test_der_encode_int(input: int, expected: bytes) -> None:
    assert der_encode_int(input) == expected


@pytest.mark.parametrize(
    "input,length,expected",
    [
        (None, 32, b"\x00"),
        (0x42, 1, b"\x01\x42"),
        (0x42, 2, b"\x02\x00\x42"),
        (0x42, 8, b"\x08\x00\x00\x00\x00\x00\x00\x00\x42"),
        (b"\x42", 1, b"\x01\x42"),
        (b"\x42", 2, b"\x02\x00\x42"),
    ],
)
def test_encode_fixed(input: int, length: int, expected: bytes) -> None:
    assert encode_fixed(input, length) == expected


def test_encode_fixed_int_too_big() -> None:
    with pytest.raises(OverflowError):
        encode_fixed(0x1234567890, 4)


def test_encode_fixed_bytes_too_long() -> None:
    with pytest.raises(OverflowError):
        encode_fixed(b"\x12\x34\x56\x78\x90", 4)
