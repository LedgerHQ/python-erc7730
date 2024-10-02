from typing import Annotated, Any, ForwardRef

from pydantic import Discriminator, Tag
from pydantic import Field as PydanticField

from erc7730.common.properties import has_property
from erc7730.model.base import Model
from erc7730.model.display import (
    AddressNameParameters,
    CallDataParameters,
    DateParameters,
    FieldFormat,
    FieldsBase,
    FormatBase,
    NftNameParameters,
    TokenAmountParameters,
    UnitParameters,
)
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputReference(FieldsBase):
    ref: str = PydanticField(alias="$ref")
    params: dict[str, str] | None = None  # FIXME wrong


class InputEnumParameters(Model):
    ref: str = PydanticField(alias="$ref")


def get_param_discriminator(v: Any) -> str | None:
    if has_property(v, "tokenPath"):
        return "token_amount"
    if has_property(v, "encoding"):
        return "date"
    if has_property(v, "collectionPath"):
        return "nft_name"
    if has_property(v, "base"):
        return "unit"
    if has_property(v, "$ref"):
        return "enum"
    if has_property(v, "type"):
        return "address_name"
    if has_property(v, "selector"):
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


class InputFieldDefinition(Model):
    id: Id | None = PydanticField(None, alias="$id")
    label: str
    format: FieldFormat | None
    params: InputFieldParameters | None = None


class InputFieldDescription(InputFieldDefinition, FieldsBase):
    pass


class InputNestedFields(FieldsBase):
    fields: list[ForwardRef("InputField")]  # type: ignore


def get_field_discriminator(v: Any) -> str | None:
    if has_property(v, "$ref"):
        return "reference"
    if has_property(v, "fields"):
        return "nested_fields"
    if has_property(v, "label"):
        return "field_description"
    return None


InputField = Annotated[
    Annotated[InputReference, Tag("reference")]
    | Annotated[InputFieldDescription, Tag("field_description")]
    | Annotated[InputNestedFields, Tag("nested_fields")],
    Discriminator(get_field_discriminator),
]


InputNestedFields.model_rebuild()


class InputFormat(FormatBase):
    fields: list[InputField]


class InputDisplay(Model):
    definitions: dict[str, InputFieldDefinition] | None = None
    formats: dict[str, InputFormat]
