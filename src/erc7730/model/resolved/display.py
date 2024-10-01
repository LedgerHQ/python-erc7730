from typing import Annotated, Any, ForwardRef

from pydantic import Discriminator, RootModel, Tag
from pydantic import Field as PydanticField

from erc7730.model.base import Model
from erc7730.model.display import (
    AddressNameParameters,
    CallDataParameters,
    DateParameters,
    FieldFormat,
    NftNameParameters,
    Screen,
    TokenAmountParameters,
    UnitParameters,
)
from erc7730.model.types import Id, Path

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ResolvedFieldsBase(Model):
    path: str


class ResolvedEnumParameters(Model):
    ref: str = PydanticField(alias="$ref")  # TODO must be inlined here


def get_param_discriminator(v: Any) -> str | None:
    if isinstance(v, dict):
        if v.get("tokenPath") is not None:
            return "token_amount"
        if v.get("collectionPath") is not None:
            return "nft_name"
        if v.get("encoding") is not None:
            return "date"
        if v.get("base") is not None:
            return "unit"
        if v.get("$ref") is not None:
            return "enum"
        if v.get("type") is not None or v.get("sources") is not None:
            return "address_name"
        if v.get("selector") is not None or v.get("calleePath") is not None:
            return "call_data"
        return None
    if getattr(v, "tokenPath", None) is not None:
        return "token_amount"
    if getattr(v, "encoding", None) is not None:
        return "date"
    if getattr(v, "collectionPath", None) is not None:
        return "nft_name"
    if getattr(v, "base", None) is not None:
        return "unit"
    if getattr(v, "$ref", None) is not None:
        return "enum"
    if getattr(v, "type", None) is not None:
        return "address_name"
    if getattr(v, "selector", None) is not None:
        return "call_data"
    return None


ResolvedFieldParameters = Annotated[
    Annotated[AddressNameParameters, Tag("address_name")]
    | Annotated[CallDataParameters, Tag("call_data")]
    | Annotated[TokenAmountParameters, Tag("token_amount")]
    | Annotated[NftNameParameters, Tag("nft_name")]
    | Annotated[DateParameters, Tag("date")]
    | Annotated[UnitParameters, Tag("unit")]
    | Annotated[ResolvedEnumParameters, Tag("enum")],
    Discriminator(get_param_discriminator),
]


class ResolvedFieldDescription(Model):
    id: Id | None = PydanticField(None, alias="$id")
    path: Path
    label: str
    format: FieldFormat | None
    params: ResolvedFieldParameters | None = None


class ResolvedNestedFields(ResolvedFieldsBase):
    fields: list[ForwardRef("ResolvedField")]


def get_field_discriminator(v: Any) -> str | None:
    if isinstance(v, dict):
        if v.get("label") is not None and v.get("format") is not None:
            return "field_description"
        if v.get("fields") is not None:
            return "nested_fields"
        return None
    if getattr(v, "label", None) is not None:
        return "field_description"
    if getattr(v, "fields", None) is not None:
        return "nested_fields"
    return None


class ResolvedField(
    RootModel[
        Annotated[
            Annotated[ResolvedFieldDescription, Tag("field_description")]
            | Annotated[ResolvedNestedFields, Tag("nested_fields")],
            Discriminator(get_field_discriminator),
        ]
    ]
):
    """Field"""


ResolvedNestedFields.model_rebuild()


class ResolvedFormat(Model):
    id: Id | None = PydanticField(None, alias="$id")
    intent: str | dict[str, str] | None = None
    fields: list[ResolvedField]
    required: list[str] | None = None
    screens: dict[str, list[Screen]] | None = None


class ResolvedDisplay(Model):
    definitions: dict[str, ResolvedFieldDescription] | None = None
    formats: dict[str, ResolvedFormat]
