from pathlib import Path
from typing import Optional

from pydantic import Field

from erc7730.common.pydantic import (
    model_from_json_file_with_includes,
    model_from_json_file_with_includes_or_none,
    model_to_json_str,
)
from erc7730.model.base import Model
from erc7730.model.context import ContractContext, EIP712Context
from erc7730.model.display import Display
from erc7730.model.metadata import Metadata

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ERC7730Descriptor(Model):
    """
    An ERC7730 Clear Signing descriptor.

    Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs

    JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
    """

    schema_: str | None = Field(None, alias="$schema")
    context: ContractContext | EIP712Context
    metadata: Metadata
    display: Display

    @classmethod
    def load(cls, path: Path) -> "ERC7730Descriptor":
        """
        Load an ERC7730 descriptor from a JSON file.

        :param path: file path
        :return: validated in-memory representation of descriptor
        :raises Exception: if the file does not exist or has validation errors
        """
        return model_from_json_file_with_includes(path, ERC7730Descriptor)

    @classmethod
    def load_or_none(cls, path: Path) -> Optional["ERC7730Descriptor"]:
        """
        Load an ERC7730 descriptor from a JSON file.

        :param path: file path
        :return: validated in-memory representation of descriptor, or None if file does not exist
        :raises Exception: if the file has validation errors
        """
        return model_from_json_file_with_includes_or_none(path, ERC7730Descriptor)

    def to_json_string(self) -> str:
        """
        Serialize the descriptor to a JSON string.

        :return: JSON representation of descriptor, serialized as a string
        """
        return model_to_json_str(self)
