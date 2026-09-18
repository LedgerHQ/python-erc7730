"""
Conversion of ERC-7730 enum definitions to calldata descriptor instructions.
"""

from erc7730.model.calldata.v1.instruction import (
    CalldataDescriptorInstructionEnumValueV1,
)
from erc7730.model.metadata import EnumDefinition
from erc7730.model.resolved.context import ResolvedDeployment
from erc7730.model.types import Id, Selector

# A bool holds 0 or 1 in calldata, and an enum key is the field value it matches, so these are
# the keys a descriptor writes for a bool field. JSON has no bool object key, so they arrive as
# text, and the casing follows whoever wrote the descriptor rather than any rule.
BOOLEAN_ORDINALS = {"true": 1, "false": 0}


def enum_ordinal(ordinal: str) -> int:
    """Value the device compares an enum entry against.

    :param ordinal: enum key, as written in the descriptor
    :return: the numeric field value it stands for
    :raises ValueError: if the key is neither decimal nor a boolean literal
    """
    try:
        return int(ordinal)
    except ValueError:
        if (value := BOOLEAN_ORDINALS.get(ordinal.strip().lower())) is not None:
            return value
        raise


def convert_enums(
    deployment: ResolvedDeployment, selector: Selector, enums: dict[Id, EnumDefinition] | None
) -> list[CalldataDescriptorInstructionEnumValueV1]:
    """
    Convert descriptor enum definitions to calldata descriptor enum value instructions.

    @param enums: descriptor enum definitions
    @return: instructions for each enum entry
    """
    if enums is None:
        return []

    return [
        CalldataDescriptorInstructionEnumValueV1(
            chain_id=deployment.chainId,
            address=deployment.address,
            selector=selector,
            id=i,
            enum_id=enum_id,
            value=enum_ordinal(ordinal),
            name=name,
        )
        for i, (enum_id, enum) in enumerate(enums.items())
        for ordinal, name in enum.items()
    ]
