"""
Utilities for manipulating ERC-7730 descriptors.
"""

from erc7730.model.input.context import Deployments, InputContractContext, InputEIP712Context
from erc7730.model.input.descriptor import InputERC7730Descriptor


def get_chain_ids(descriptor: InputERC7730Descriptor) -> set[int] | None:
    """Get deployment chaind ids for a descriptor."""
    if (deployments := get_deployments(descriptor)) is None:
        return None
    return {d.chainId for d in deployments.root}


def get_deployments(descriptor: InputERC7730Descriptor) -> Deployments | None:
    """Get deployments section for a descriptor."""
    if isinstance(context := descriptor.context, InputEIP712Context):
        return context.eip712.deployments
    if isinstance(context := descriptor.context, InputContractContext):
        return context.contract.deployments
    raise ValueError(f"Invalid context type {type(descriptor.context)}")
