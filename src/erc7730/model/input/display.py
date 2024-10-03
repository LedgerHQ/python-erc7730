from typing import Annotated, Any, ForwardRef

from pydantic import Discriminator, Field, Tag

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
    """
    TODO
    """

    ref: str = Field(alias="$ref", title="TODO", description="TODO")

    params: dict[str, str] | None = Field(  # FIXME wrong
        default=None, title="TODO", description="TODO"
    )


class InputEnumParameters(Model):
    """
    TODO
    """

    ref: str = Field(alias="$ref", title="TODO", description="TODO")


def get_param_discriminator(v: Any) -> str | None:
    """
    TODO
    :param v:
    :return:
    """
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
    """
    TODO
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    label: str = Field(
        title="Field Label",
        description="The label of the field, that will be displayed to the user in front of the formatted field value.",
    )

    format: FieldFormat | None = Field(title="TODO", description="TODO")

    params: InputFieldParameters | None = Field(default=None, title="TODO", description="TODO")


class InputFieldDescription(InputFieldDefinition, FieldsBase):
    """
    TODO
    """


class InputNestedFields(FieldsBase):
    """
    TODO
    """

    fields: list[ForwardRef("InputField")] = Field(  # type: ignore
        title="TODO", description="TODO"
    )


def get_field_discriminator(v: Any) -> str | None:
    """
    TODO
    :param v:
    :return:
    """
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
    """
    TODO
    """

    fields: list[InputField] = Field(title="TODO", description="TODO")


class InputDisplay(Model):
    """
    TODO
    """

    definitions: dict[str, InputFieldDefinition] | None = Field(default=None, title="TODO", description="TODO")

    formats: dict[str, InputFormat] = Field(title="TODO", description="TODO")
