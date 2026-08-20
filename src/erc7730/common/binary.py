"""Utilities for binary data manipulation."""

from enum import IntEnum


def from_hex(value: str) -> bytes:
    """
    Convert an hex string to a byte array.

    @param value: hex string (can be prefixed with 0x or not)
    @return: decoded byte array
    """
    return bytes.fromhex(value.removeprefix("0x"))


def tlv(
    tag: int | IntEnum,
    value: bytes | bytearray | str | int | None = None,
    max_length: int | None = None,
    optional: bool = False,
) -> bytes:
    """
    Encode a value in TLV format (Tag-Length-Value)

    Tag and length are DER encoded.

    If value is not encoded, it will be encoded as ASCII.
    If value is an integer, it will be encoded as smallest variable-length integer.

    If input string is not ASCII, and UnicodeEncodeError is raised.
    If encoded value is longer than max_length, OverflowError is raised.

    @param tag: the tag (can be an enum)
    @param value: the value (can be already encoded, a string or an integer)
    @param max_length: the maximum length of the value (if None, no limit)
    @param optional: if True, the TLV will be omitted if value is None, else it will be encoded as 0-length.
    @return: encoded TLV
    """
    if optional and value is None:
        return b""

    return der_encode_int(tag.value if isinstance(tag, IntEnum) else tag) + length_value(
        value, max_length, der_encode_length=True
    )


def fixed_tlv(tag: int | IntEnum, length: int, value: int | bytes | None, optional: bool = False) -> bytes:
    """
    Encode a value in TLV format (Tag-Length-Value) with a fixed length for the value.

    Tag and length are DER encoded.

    If encoded value is longer than length, OverflowError is raised. If smaller, it will be padded with zeros.

    @param tag: the tag (can be an enum)
    @param length: the length of the value
    @param value: the value (can be already encoded or an integer)
    @param optional: if True, the TLV will be omitted if value is None, else it will be encoded as 0-length.
    @return: encoded TLV
    """

    if optional and value is None:
        return b""
    return der_encode_int(tag.value if isinstance(tag, IntEnum) else tag) + encode_fixed(value, length)


def length_value(
    value: bytes | bytearray | str | int | None, max_length: int | None = None, der_encode_length: bool = False
) -> bytes:
    """
    Prepend the length (DER encoded) of the value encoded to the value itself.

    If value is not encoded, it will be encoded as ASCII.

    If input string is not ASCII, and UnicodeEncodeError is raised.
    If encoded value is longer than max_length, OverflowError is raised

    @param value: the value (can be already encoded, or a string)
    @param max_length: the maximum length of the value (if None, no limit)
    @return: encoded TLV
    """
    if value is None:
        return (0).to_bytes(1, "big")
    match value:
        case int():
            value_encoded = encode_variable_int(value)
        case bytes() | bytearray():
            value_encoded = bytes(value)
        case str():
            value_encoded = value.encode("ascii", errors="strict")
    if max_length is not None and len(value_encoded) > max_length:
        raise OverflowError(f"Value length {len(value_encoded)} exceeds maximum length {max_length}")
    if der_encode_length:
        return der_encode_int(len(value_encoded)) + value_encoded
    else:  # This will raise OverflowError if value_encoded is longer than 255 bytes
        return (len(value_encoded)).to_bytes(1, "big") + value_encoded


def der_encode_int(value: int) -> bytes:
    """
    Encode an integer in DER format.

    @param value: the integer to encode
    @return: DER encoded byte array
    """
    value_bytes = encode_variable_int(value)
    if value >= 0x80:
        value_bytes = (0x80 | len(value_bytes)).to_bytes(1, "big") + value_bytes
    return value_bytes


def encode_variable_int(value: int | None) -> bytes:
    """
    Encode an integer in variable-length format.

    @param value: the integer to encode
    @return: variable-length encoded byte array
    """
    if value is None:
        return (0).to_bytes(1, "big")
    return value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")


def encode_fixed(value: int | bytes | None, length: int) -> bytes:
    """
    Encode an integer in fixed-length format.

    If encoded value is longer than length, OverflowError is raised. If smaller, it will be padded with zeros.

    @param value: the integer to encode
    @param length: the length of the encoded value in bytes
    @return: fixed-length encoded byte array
    """
    if value is None:
        return (0).to_bytes(1, "big")
    match value:
        case int():
            value_encoded = value.to_bytes(length, "big")
        case bytes():
            original_length = len(value)
            if original_length > length:
                raise OverflowError(f"Value length {original_length} exceeds fixed length {length}")
            padding = max(0, length - original_length)
            value_encoded = (b"\0" * padding) + value
    return der_encode_int(length) + value_encoded
