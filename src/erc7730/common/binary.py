"""Utilities for binary data manipulation."""

from enum import IntEnum


def from_hex(value: str) -> bytes:
    """
    Convert an hex string to a byte array.

    @param value: hex string (can be prefixed with 0x or not)
    @return: decoded byte array
    """
    return bytes.fromhex(value.removeprefix("0x"))


def tlv(tag: int | IntEnum, value: bytes | str | None = None) -> bytes:
    """
    Encode a value in TLV format (Tag-Length-Value)

    Tag and length are DER encoded. If tag value or length exceed 255, an OverflowError is raised.

    If value is not encoded, it will be encoded as ASCII.
    If input string is not ASCII, a UnicodeEncodeError is raised.

    @param tag: the tag (can be an enum)
    @param value: the value (can be already encoded, a string or None)
    @return: encoded TLV
    """

    return der_encode_int(tag.value if isinstance(tag, IntEnum) else tag) + length_value(value)


def length_value(
    value: bytes | str | None,
) -> bytes:
    """
    Prepend the length (DER encoded) of the value encoded to the value itself.
    If length exceeds 255 bytes, an OverflowError is raised.

    If value is not encoded, it will be encoded as ASCII.
    If input string is not ASCII, a UnicodeEncodeError is raised.

    @param value: the value (can be already encoded, or a string)
    @return: encoded TLV
    """
    if value is None:
        return (0).to_bytes(1, "big")
    match value:
        case bytes():
            value_encoded = value
        case str():
            value_encoded = value.encode("ascii", errors="strict")
    return der_encode_int(len(value_encoded)) + value_encoded


def der_encode_int(value: int) -> bytes:
    """
    Encode an integer in DER format.
    If value exceeds 255, an OverflowError is raised.

    @param value: the integer to encode
    @return: DER encoded byte array
    """
    value_bytes = value.to_bytes(1, "big")  # raises OverflowError if value >= 256
    return (0x81).to_bytes(1, "big") + value_bytes if value >= 0x80 else value_bytes
