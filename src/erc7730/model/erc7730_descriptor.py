from pathlib import Path
from typing import Union, Optional

from pydantic import ConfigDict, Field

from erc7730.common.pydantic import model_from_json_file_with_includes, model_from_json_file_with_includes_or_none
from erc7730.model.base import BaseLibraryModel
from erc7730.model.context import ContractContext, EIP712Context
from erc7730.model.display import Display
from erc7730.model.metadata import Metadata


class ERC7730Descriptor(BaseLibraryModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        validate_default=True,
        validate_return=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        allow_inf_nan=False,
    )
    field_schema: Optional[str] = Field(None, alias="$schema")
    context: Optional[Union[ContractContext, EIP712Context]] = None
    metadata: Optional[Metadata] = None
    display: Optional[Display] = None

    @classmethod
    def load(cls, path: Path) -> "ERC7730Descriptor":
        return model_from_json_file_with_includes(path, ERC7730Descriptor)

    @classmethod
    def load_or_none(cls, path: Path) -> Optional["ERC7730Descriptor"]:
        return model_from_json_file_with_includes_or_none(path, ERC7730Descriptor)
