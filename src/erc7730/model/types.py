"""
Base types for ERC-7730 descriptors.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

import re
from typing import Annotated

from eth_utils.address import to_checksum_address
from pydantic import AfterValidator, BeforeValidator, Field
from pydantic_core import PydanticCustomError

from erc7730.common.pydantic import ErrorTypeLabel

ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
"""The shape of an address, without the checksum."""


def validate_address_checksum(value: str) -> str:
    """
    Reject an address that is neither in lowercase nor in its EIP-55 checksum form.

    An address written in lowercase only carries no checksum and is accepted as is. An address with an uppercase
    letter claims a checksum, so a mismatch is most likely a typo or a corrupted copy. This includes an address
    written in uppercase only: EIP-55 does not define it as a form without checksum.

    The chain-specific checksum of EIP-1191 (used by Rootstock) is not supported: the type does not know the chain.
    """
    if value == value.lower():
        return value
    if value != (expected := to_checksum_address(value)):
        raise PydanticCustomError(
            "address_checksum",
            'invalid EIP-55 checksum for address "{value}", expected "{expected}" (or the address in lowercase)',
            {"value": value, "expected": expected},
        )
    return value


Id = Annotated[
    str,
    Field(
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a "
        "reference in device specific sections.",
        min_length=1,
        examples=["some_identifier"],
    ),
    ErrorTypeLabel('identifier, such as "some_identifier".'),
]

MixedCaseAddress = Annotated[
    str,
    Field(
        title="Contract Address",
        description="An Ethereum contract address, can be lowercase or EIP-55.",
        min_length=42,
        max_length=42,
        pattern=ADDRESS_PATTERN.pattern,
    ),
    ErrorTypeLabel(
        '20 bytes, hexadecimal Ethereum address prefixed with "0x" (EIP-55 or lowercase), such as '
        + '"0xdac17f958d2ee523a2206206994597c13d831ec7".'
    ),
    # after the label wrapper, so that a checksum error keeps its own message
    AfterValidator(validate_address_checksum),
]

Address = Annotated[
    str,
    Field(
        title="Contract Address",
        description="An Ethereum contract address (normalized to lowercase).",
        min_length=42,
        max_length=42,
        pattern=r"^0x[a-f0-9]+$",
    ),
    BeforeValidator(lambda v: v.lower()),
    ErrorTypeLabel(
        '20 bytes, lowercase hexadecimal Ethereum address prefixed with "0x", such as '
        + '"0xdac17f958d2ee523a2206206994597c13d831ec7".'
    ),
]

Selector = Annotated[
    str,
    Field(
        title="Selector",
        description="An Ethereum contract function identifier, in 4 bytes, hex encoded form.",
        min_length=10,
        max_length=10,
        pattern=r"^0x[a-z0-9]+$",
    ),
    ErrorTypeLabel(
        '4 bytes, lowercase hexadecimal Ethereum function selector prefixed with "0x", such as ' + '"0xdac17f95".'
    ),
]

HexStr = Annotated[
    str,
    Field(
        title="Hexadecimal string",
        description="A byte array encoded as an hexadecimal string.",
        pattern=r"^0x[a-f0-9]+$",
    ),
    BeforeValidator(lambda v: v.lower()),
    ErrorTypeLabel('lowercase hexadecimal string prefixed with "0x", such as "0xdac17f95".'),
]

ScalarType = str | int | bool | float
