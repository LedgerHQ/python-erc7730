"""
Base types for ERC-7730 descriptors.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

from typing import Annotated

from pydantic import BeforeValidator, Field

Id = Annotated[
    str,
    Field(
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
        min_length=1,
    ),
]

Address = Annotated[
    str,
    Field(
        title="Contract Address",
        description="An Ethereum contract address.",
        min_length=42,
        max_length=42,
        pattern=r"^0x[a-zA-Z0-9_\-]+$",
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
]

HexStr = Annotated[
    str,
    Field(
        title="Hexadecimal string",
        description="A byte array encoded as an hexadecimal string.",
        pattern=r"^0x[a-f0-9]+$",
    ),
    BeforeValidator(lambda v: v.lower()),
]

ScalarType = str | int | bool | float
