"""
Data model for Ledger specific calldata descriptor, version 1 (also referred to as "generic parser" descriptor).
"""

from typing import Literal

from pydantic import Field

from erc7730.model.calldata import CalldataDescriptorBase
from erc7730.model.calldata.v1.eip712 import (
    CalldataDescriptorInstructionEIP712SchemaV1,
)
from erc7730.model.calldata.v1.instruction import (
    CalldataDescriptorInstructionEIP712MessageInfoV1,
    CalldataDescriptorInstructionEnumValueV1,
    CalldataDescriptorInstructionFieldV1,
    CalldataDescriptorInstructionTransactionInfoV1,
)
from erc7730.model.types import HexStr, Selector


class CalldataDescriptorV1(CalldataDescriptorBase):
    """
    A clear signing descriptor for a smart contract function calldata.

    Also referred to as a "generic parser descriptor".
    """

    type: Literal["calldata"] = Field(
        default="calldata",
        title="Descriptor type",
        description="Type of the descriptor (contract calldata).",
    )

    selector: Selector = Field(
        title="Function selector",
        description="The 4-bytes function selector this descriptor applies to.",
    )

    version: Literal["v1"] = Field(
        default="v1",
        title="Descriptor type version",
        description="Version of the descriptor type (not the version of this specific descriptor, the version of the "
        "descriptor specification)",
    )

    transaction_info: CalldataDescriptorInstructionTransactionInfoV1 = Field(
        title="TRANSACTION_INFO instruction descriptor",
        description="Descriptor and metadata to craft a TRANSACTION_INFO APDU.",
    )

    enums: list[CalldataDescriptorInstructionEnumValueV1] = Field(
        title="ENUM_VALUE instructions descriptors",
        description="Descriptor and metadata to craft ENUM APDUs.",
    )

    fields: list[CalldataDescriptorInstructionFieldV1] = Field(
        title="FIELD instructions descriptors",
        description="Descriptor and metadata to craft FIELD APDUs.",
    )


class CalldataDescriptorEIP712V1(CalldataDescriptorBase):
    """
    A clear signing descriptor for an EIP-712 typed message.

    Reuses the calldata (generic parser) v1 FIELD / PARAM_* / ENUM_VALUE structs, adding the EIP712_SCHEMA and
    EIP712_MESSAGE_INFO structs and the EIP712_PATH value source. Referred to as "EIP712 v2" in the Ethereum app
    specifications.
    """

    type: Literal["eip712"] = Field(
        default="eip712",
        title="Descriptor type",
        description="Type of the descriptor (EIP-712 message).",
    )

    version: Literal["v1"] = Field(
        default="v1",
        title="Descriptor type version",
        description="Version of the descriptor type (not the version of this specific descriptor, the version of the "
        "descriptor specification)",
    )

    primary_type_hash: HexStr = Field(
        title="Primary type hash",
        description="keccak256(encodeType(primaryType)) of the EIP-712 message primary type.",
        min_length=64,
        max_length=66,
    )

    schema_info: CalldataDescriptorInstructionEIP712SchemaV1 = Field(
        title="EIP712_SCHEMA instruction descriptor",
        description="Descriptor and metadata to craft an EIP712_SCHEMA APDU.",
    )

    message_info: CalldataDescriptorInstructionEIP712MessageInfoV1 = Field(
        title="EIP712_MESSAGE_INFO instruction descriptor",
        description="Descriptor and metadata to craft an EIP712_MESSAGE_INFO APDU.",
    )

    enums: list[CalldataDescriptorInstructionEnumValueV1] = Field(
        title="ENUM_VALUE instructions descriptors",
        description="Descriptor and metadata to craft ENUM APDUs.",
    )

    fields: list[CalldataDescriptorInstructionFieldV1] = Field(
        title="EIP712_FIELD_DESCRIPTOR instructions descriptors",
        description="Descriptor and metadata to craft EIP712_FIELD_DESCRIPTOR APDUs.",
    )
