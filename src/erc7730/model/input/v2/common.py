"""
Shared types for ERC-7730 v2 input descriptors.

This module contains types used across multiple v2 input modules (display, context, metadata)
to avoid circular imports.
"""

from pydantic import Field

from erc7730.model.base import Model
from erc7730.model.input.path import ContainerPathStr, DataPathStr, DescriptorPathStr

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputMapReference(Model):
    """
    A reference to a map for dynamic value resolution.
    """

    map: DescriptorPathStr = Field(
        title="Map Reference",
        description="The path to the referenced map.",
    )

    keyPath: DescriptorPathStr | DataPathStr | ContainerPathStr = Field(
        title="Key Path",
        description="The path to the key used to resolve a value in the referenced map.",
    )
