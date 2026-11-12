"""
Data model for the EIP712_SCHEMA calldata descriptor struct and its nested structs.

These model classes represent the exact same data fields that are serialized into TLV structs. Referred to as
"EIP712 v2" in the Ethereum app specifications (https://github.com/LedgerHQ/app-ethereum), but part of the calldata
(generic parser) v1 descriptor format.
"""

from enum import IntEnum
from functools import cached_property
from typing import Literal, Self

from pydantic import Field, computed_field, model_validator

from erc7730.common.pydantic import pydantic_enum_by_name
from erc7730.model.base import Model
from erc7730.model.calldata.v1.instruction import (
    CalldataDescriptorInstructionBaseV1,
    CalldataDescriptorInstructionHex,
)


@pydantic_enum_by_name
class CalldataDescriptorEIP712SolType(IntEnum):
    """Solidity base type of an EIP-712 struct field (EIP712_FIELD TYPE / SolType enum)."""

    STRUCT = 0x00
    INT = 0x01
    UINT = 0x02
    ADDRESS = 0x03
    BOOL = 0x04
    STRING = 0x05
    BYTES_FIX = 0x06
    BYTES_DYN = 0x07


# limits of the device (doc/eip712.md#implementation-limits in app-ethereum-dev)
MAX_ARRAY_DIMENSIONS = 8
MAX_ARRAY_DIMENSION_SIZE = 255

# base types carrying a TYPE_SIZE
_SIZED_TYPES = (
    CalldataDescriptorEIP712SolType.INT,
    CalldataDescriptorEIP712SolType.UINT,
    CalldataDescriptorEIP712SolType.BYTES_FIX,
)


class CalldataDescriptorEIP712FieldV1(Model):
    """Descriptor for the EIP712_FIELD struct (one field of an EIP-712 struct type)."""

    name: str = Field(
        title="Field name",
        description="Field name (ASCII)",
        min_length=1,
    )

    sol_type: CalldataDescriptorEIP712SolType = Field(
        title="Solidity type",
        description="Solidity base type of the field",
    )

    type_size: int | None = Field(
        default=None,
        title="Type size",
        description="Size in bytes, for INT/UINT/BYTES_FIX (1..32).",
        ge=1,
        le=32,
    )

    # innermost dimension first; None entry means a dynamic dimension, int means a fixed dimension size
    array_dimensions: list[int | None] = Field(
        default_factory=list,
        title="Array dimensions",
        description="One entry per array dimension, innermost first. None means dynamic dimension, an integer means "
        "the fixed dimension size.",
    )

    struct_name: str | None = Field(
        default=None,
        title="Struct name",
        description="Referenced struct name, only set if the type is STRUCT.",
    )

    @model_validator(mode="after")
    def _validate_field(self) -> Self:
        if any(c in self.name for c in "(),"):
            raise ValueError(f'Field name "{self.name}" cannot contain "(", ")" or ",".')
        if (self.sol_type in _SIZED_TYPES) != (self.type_size is not None):
            raise ValueError(f"A type size is required for INT, UINT and BYTES_FIX only, got {self.sol_type.name}.")
        if (self.sol_type == CalldataDescriptorEIP712SolType.STRUCT) != (self.struct_name is not None):
            raise ValueError(f"A struct name is required for STRUCT only, got {self.sol_type.name}.")
        if len(self.array_dimensions) > MAX_ARRAY_DIMENSIONS:
            raise ValueError(f"At most {MAX_ARRAY_DIMENSIONS} array dimensions are supported per field.")
        if any(d is not None and not 0 <= d <= MAX_ARRAY_DIMENSION_SIZE for d in self.array_dimensions):
            raise ValueError(f"Fixed array dimensions must be between 0 and {MAX_ARRAY_DIMENSION_SIZE}.")
        return self


class CalldataDescriptorEIP712StructV1(Model):
    """Descriptor for the EIP712_STRUCT struct (one EIP-712 struct type declaration)."""

    name: str = Field(
        title="Struct name",
        description="Struct name (ASCII). 'EIP712Domain' identifies the domain struct.",
        min_length=1,
    )

    fields: list[CalldataDescriptorEIP712FieldV1] = Field(
        title="Fields",
        description="One entry per declared field, in declaration order.",
    )

    @model_validator(mode="after")
    def _validate_struct(self) -> Self:
        if any(c in self.name for c in " ()[],"):
            raise ValueError(f'Struct name "{self.name}" cannot contain a space or any of "(", ")", "[", "]", ",".')
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError(f'Struct "{self.name}" has several fields of the same name.')
        return self


class CalldataDescriptorInstructionEIP712SchemaV1(CalldataDescriptorInstructionBaseV1):
    """Instruction descriptor for the EIP712_SCHEMA struct (whole schema, all struct types nested)."""

    version: Literal[1] = Field(
        default=1,
        title="Struct version",
        description="Version of the EIP712_SCHEMA struct",
    )

    structs: list[CalldataDescriptorEIP712StructV1] = Field(
        title="Structs",
        description="One entry per declared struct type.",
        min_length=1,
    )

    @model_validator(mode="after")
    def _validate_schema(self) -> Self:
        names = [struct.name for struct in self.structs]
        if len(set(names)) != len(names):
            raise ValueError("The schema has several structs of the same name.")
        if "EIP712Domain" not in names:
            raise ValueError("The schema must contain the EIP712Domain struct.")
        return self

    @computed_field(title="Descriptor", description="Hex encoded EIP712_SCHEMA TLV struct")  # type: ignore[misc]
    @cached_property
    def descriptor(self) -> CalldataDescriptorInstructionHex:
        from erc7730.convert.calldata.v1.tlv import tlv_eip712_schema

        return tlv_eip712_schema(self).hex()
