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


class InputFieldsBase(Model):
    path: str


class InputReference(InputFieldsBase):
    ref: str = PydanticField(alias="$ref")
    params: dict[str, str] | None = None


class InputEnumParameters(Model):
    ref: str = PydanticField(alias="$ref")


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


InputFieldParameters = Annotated[
    Annotated[AddressNameParameters, Tag("address_name")]
    | Annotated[CallDataParameters, Tag("call_data")]
    | Annotated[TokenAmountParameters, Tag("token_amount")]
    | Annotated[NftNameParameters, Tag("nft_name")]
    | Annotated[DateParameters, Tag("date")]
    | Annotated[UnitParameters, Tag("unit")]
    | Annotated[InputEnumParameters, Tag("enum")],
    Discriminator(get_param_discriminator),
]


class InputFieldDescription(Model):
    id: Id | None = PydanticField(None, alias="$id")
    path: Path
    label: str
    format: FieldFormat | None
    params: InputFieldParameters | None = None


class InputNestedFields(InputFieldsBase):
    fields: list[ForwardRef("InputField")]  # type: ignore


def get_field_discriminator(v: Any) -> str | None:
    if isinstance(v, dict):
        if v.get("label") is not None and v.get("format") is not None:
            return "field_description"
        if v.get("fields") is not None:
            return "nested_fields"
        if v.get("$ref") is not None:
            return "reference"
        return None
    if getattr(v, "label", None) is not None:
        return "field_description"
    if getattr(v, "fields", None) is not None:
        return "nested_fields"
    if getattr(v, "ref", None) is not None:
        return "reference"
    return None


class InputField(
    RootModel[
        Annotated[
            Annotated[InputReference, Tag("reference")]
            | Annotated[InputFieldDescription, Tag("field_description")]
            | Annotated[InputNestedFields, Tag("nested_fields")],
            Discriminator(get_field_discriminator),
        ]
    ]
):
    """Field"""


InputNestedFields.model_rebuild()


class InputFormat(Model):
    id: Id | None = PydanticField(None, alias="$id")
    intent: str | dict[str, str] | None = None
    fields: list[InputField]
    required: list[str] | None = None
    screens: dict[str, list[Screen]] | None = None


class InputDisplay(Model):
    definitions: dict[str, InputFieldDescription] | None = None
    formats: dict[str, InputFormat]
