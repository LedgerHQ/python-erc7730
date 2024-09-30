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
    field_schema: str | None = Field(None, alias="$schema")
    context: ContractContext | EIP712Context | None = None
    metadata: Metadata | None = None
    display: Display | None = None

    @classmethod
    def load(cls, path: Path) -> "ERC7730Descriptor":
        return model_from_json_file_with_includes(path, ERC7730Descriptor)

    @classmethod
    def load_or_none(cls, path: Path) -> Optional["ERC7730Descriptor"]:
        return model_from_json_file_with_includes_or_none(path, ERC7730Descriptor)

    def to_json_string(self) -> str:
        return model_to_json_str(self)
