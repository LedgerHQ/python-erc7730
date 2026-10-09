"""
Data model for calldata descriptor instructions.

These model classes represent the exact same data fields that are serialized into TLV structs.
See documentation in https://github.com/LedgerHQ/app-ethereum for specifications of this protocol
"""

from abc import ABC
from enum import IntEnum
from functools import cached_property
from typing import Annotated, Literal, Self

from pydantic import Field, computed_field, model_validator
from pydantic_string_url import HttpUrl

from erc7730.common.pydantic import pydantic_enum_by_name
from erc7730.model.calldata.v1.param import (
    CalldataDescriptorParamV1,
)
from erc7730.model.calldata.v1.struct import (
    CalldataDescriptorStructV1,
)
from erc7730.model.types import Address, HexStr, ScalarType, Selector

CalldataDescriptorInstructionHex = Annotated[
    HexStr,
    Field(
        title="Serialized TLV instruction payload",
        description="Serialized, hex encoded TLV payload.",
        min_length=8,
        max_length=32768,
    ),
]

CalldataDescriptorInstructionProtobuf = Annotated[
    HexStr,
    Field(
        title="Serialized production signature payload",
        description="Serialized, hex encoded Protobuf payload used for production signature.",
        min_length=8,
        max_length=32768,
    ),
]


# maximum number of CONSTRAINT tags per FIELD struct, as documented in app-ethereum
MAX_FIELD_CONSTRAINTS = 5

# maximum size of a MAP_ENTRY key or value (MAP_ENTRY_MAX_KEY_SIZE / MAP_ENTRY_MAX_VALUE_SIZE in app-ethereum)
MAX_MAP_ENTRY_SIZE = 32


@pydantic_enum_by_name
class CalldataDescriptorFieldVisibilityV1(IntEnum):
    """
    Visibility of a calldata field (``VisibleType`` in the FIELD struct).

    ``MUST_BE`` and ``IF_NOT_IN`` require at least one constraint value; the device rejects the
    transaction when a ``MUST_BE`` value matches no constraint.
    """

    ALWAYS = 0x00
    MUST_BE = 0x01
    IF_NOT_IN = 0x02


# extra must be ignored because of descriptor computed field
class CalldataDescriptorInstructionBaseV1(CalldataDescriptorStructV1, ABC, extra="ignore"):
    """Base class for calldata descriptor instructions."""


class CalldataDescriptorInstructionTransactionInfoV1(CalldataDescriptorInstructionBaseV1):
    """Instruction descriptor for the TRANSACTION_INFO struct."""

    version: Literal[1] = Field(
        default=1,
        title="Struct version",
        description="Version of the TRANSACTION_INFO struct",
    )

    chain_id: int = Field(
        title="Chain ID",
        description="The contract deployment EIP-155 chain id.",
        ge=1,
    )

    address: Address = Field(
        title="Contract address",
        description="The contract deployment address.",
    )

    selector: Selector = Field(
        title="Function selector",
        description="The 4-bytes function selector this descriptor applies to.",
    )

    hash: str = Field(
        title="Structs hash",
        description="Hash of all the FIELD structs",
        pattern=r"^[a-f0-9]+$",
        min_length=64,
        max_length=64,
    )

    operation_type: str = Field(
        title="Operation type",
        description="Displayed in review first screens",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    creator_name: str | None = Field(
        default=None,
        title="Creator name",
        description="Displayed in review first screens",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    creator_legal_name: str | None = Field(
        default=None,
        title="Creator legal name",
        description="Displayed in review first screens",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    creator_url: HttpUrl | None = Field(
        default=None,
        title="Creator URL",
        description="Displayed in review first screens",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    contract_name: str | None = Field(
        default=None,
        title="Contract name",
        description="Displayed in review first screens",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    deploy_date: str | None = Field(
        default=None,
        title="Deploy date",
        description="Displayed in review first screens",
    )

    @computed_field(title="Descriptor", description="Hex encoded TRANSACTION_INFO TLV struct")  # type: ignore[misc]
    @cached_property
    def descriptor(self) -> CalldataDescriptorInstructionHex:
        from erc7730.convert.calldata.v1.tlv import (
            tlv_transaction_info,
        )

        return tlv_transaction_info(self).hex()


class CalldataDescriptorInstructionEnumValueV1(CalldataDescriptorInstructionBaseV1):
    """Instruction descriptor for the ENUM_VALUE struct."""

    version: Literal[1] = Field(
        default=1,
        title="Struct version",
        description="Version of the ENUM struct",
    )

    chain_id: int = Field(
        title="Chain ID",
        description="The contract deployment EIP-155 chain id.",
        ge=1,
    )

    address: Address = Field(
        title="Contract address",
        description="The contract deployment address.",
    )

    selector: Selector = Field(
        title="Function selector",
        description="The 4-bytes function selector this descriptor applies to.",
    )

    enum_id: str = Field(
        title="Source enum identifier",
        description="Source identifier of the enum (to differentiate multiple enums in one contract)",
    )

    id: int = Field(
        title="Enum identifier",
        description="Identifier of the enum (to differentiate multiple enums in one contract)",
        ge=0,
        le=255,
    )

    value: int = Field(
        title="Enum entry value",
        description="Identifier of this specific entry (ordinal of the entry, type agnostic)",
        ge=0,
        le=255,
    )

    name: str = Field(
        title="Enum entry name",
        description="Enum display name (ASCII)",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    @computed_field(title="Descriptor", description="Hex encoded ENUM TLV struct")  # type: ignore[misc]
    @cached_property
    def descriptor(self) -> CalldataDescriptorInstructionHex:
        from erc7730.convert.calldata.v1.tlv import tlv_enum_value

        return tlv_enum_value(self).hex()


class CalldataDescriptorInstructionMapEntryV1(CalldataDescriptorInstructionBaseV1):
    """
    Instruction descriptor for the MAP_ENTRY struct.

    One struct is emitted per key of a map looked up by the device (see MAP_REF values). The wallet only provides the
    entry matching the key read from the transaction, after it has been signed with the calldata key.
    """

    version: Literal[1] = Field(
        default=1,
        title="Struct version",
        description="Version of the MAP_ENTRY struct",
    )

    chain_id: int = Field(
        title="Chain ID",
        description="The contract deployment EIP-155 chain id.",
        ge=1,
    )

    address: Address = Field(
        title="Contract address",
        description="The contract deployment address.",
    )

    selector: Selector = Field(
        title="Function selector",
        description="The 4-bytes function selector this descriptor applies to.",
    )

    map: str = Field(
        title="Source map reference",
        description="Path of the map in the source descriptor.",
    )

    id: int = Field(
        title="Map identifier",
        description="Identifier of the map (to differentiate multiple maps in one contract)",
        ge=0,
        le=255,
    )

    key_source: str = Field(
        title="Source map key",
        description="The map key, as written in the source descriptor.",
    )

    key: HexStr = Field(
        title="Map key",
        description="The map key, encoded as the device reads it from the transaction (raw bytes, hex encoded).",
    )

    value_source: ScalarType = Field(
        title="Source map value",
        description="The map value, as written in the source descriptor.",
    )

    value: HexStr = Field(
        title="Map value",
        description="The map value, encoded for the device (raw bytes, hex encoded).",
    )

    @model_validator(mode="after")
    def _validate_sizes(self) -> Self:
        # key and value are copied into fixed size buffers by the device (MAP_ENTRY_MAX_KEY_SIZE,
        # MAP_ENTRY_MAX_VALUE_SIZE), and an empty one is rejected
        for name, payload in (("key", self.key), ("value", self.value)):
            digits = payload.removeprefix("0x")
            if len(digits) % 2 != 0:
                raise ValueError(f"Map entry {name} must be whole bytes, got {len(digits)} hex digits.")
            if not 1 <= len(digits) // 2 <= MAX_MAP_ENTRY_SIZE:
                raise ValueError(f"Map entry {name} must be 1 to {MAX_MAP_ENTRY_SIZE} bytes, got {len(digits) // 2}.")
        return self

    @computed_field(title="Descriptor", description="Hex encoded MAP_ENTRY TLV struct")  # type: ignore[misc]
    @cached_property
    def descriptor(self) -> CalldataDescriptorInstructionHex:
        from erc7730.convert.calldata.v1.tlv import tlv_map_entry

        return tlv_map_entry(self).hex()


class CalldataDescriptorInstructionFieldV1(CalldataDescriptorInstructionBaseV1):
    """Instruction descriptor for the FIELD struct."""

    version: Literal[1] = Field(
        default=1,
        title="Struct version",
        description="Version of the FIELD struct",
    )

    name: str = Field(
        title="Field name",
        description="Field display name (ASCII)",
        min_length=1,
        # No max_length, may be truncated by Ethereum app
    )

    param: CalldataDescriptorParamV1 = Field(
        title="Field parameter",
        description="Parameter of the field",
    )

    visibility: CalldataDescriptorFieldVisibilityV1 = Field(
        default=CalldataDescriptorFieldVisibilityV1.ALWAYS,
        title="Field visibility",
        description="Whether the field is displayed, and whether its value is constrained",
    )

    constraints: list[HexStr] | None = Field(
        default=None,
        title="Field value constraints",
        description="Constraint values (raw bytes, hex encoded) checked against the field value, "
        "with OR semantics. Only meaningful when visibility is MUST_BE or IF_NOT_IN.",
    )

    @model_validator(mode="after")
    def _validate_constraints(self) -> Self:
        constraints = self.constraints or []
        if self.visibility is CalldataDescriptorFieldVisibilityV1.ALWAYS:
            if constraints:
                raise ValueError("Constraints are only allowed with MUST_BE or IF_NOT_IN visibility.")
            return self
        if not constraints:
            raise ValueError(f"Visibility {self.visibility.name} requires at least one constraint.")
        if len(constraints) > MAX_FIELD_CONSTRAINTS:
            raise ValueError(f"At most {MAX_FIELD_CONSTRAINTS} constraints are allowed, got {len(constraints)}.")
        for constraint in constraints:
            # a constraint is a byte array, and an odd number of digits would only fail later when
            # the TLV payload is serialized
            digits = constraint.removeprefix("0x")
            if len(digits) % 2 != 0:
                raise ValueError(f"Constraint value must be whole bytes, got {len(digits)} hex digits.")
            # size is encoded on a single byte by the device, and an empty value is rejected
            size = len(digits) // 2
            if not 1 <= size <= 255:
                raise ValueError(f"Constraint value must be 1 to 255 bytes, got {size}.")
        return self

    @computed_field(title="Descriptor", description="Hex encoded FIELD TLV struct")  # type: ignore[misc]
    @cached_property
    def descriptor(self) -> CalldataDescriptorInstructionHex:
        from erc7730.convert.calldata.v1.tlv import tlv_field

        return tlv_field(self).hex()
