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


class ResolvedEnumParameters(Model):
    """
    TODO
    """

    ref: str = Field(alias="$ref")  # TODO must be inlined here


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


class ResolvedFieldDefinition(Model):
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

    params: ResolvedFieldParameters | None = Field(default=None, title="TODO", description="TODO")


class ResolvedFieldDescription(ResolvedFieldDefinition, FieldsBase):
    """
    TODO
    """


class ResolvedNestedFields(FieldsBase):
    """
    TODO
    """

    fields: list[ForwardRef("ResolvedField")] = Field(  # type: ignore
        title="TODO", description="TODO"
    )


def get_field_discriminator(v: Any) -> str | None:
    """
    TODO
    :param v:
    :return:
    """
    if has_property(v, "fields"):
        return "nested_fields"
    if has_property(v, "label"):
        return "field_description"
    return None


ResolvedField = Annotated[
    Annotated[ResolvedFieldDescription, Tag("field_description")]
    | Annotated[ResolvedNestedFields, Tag("nested_fields")],
    Discriminator(get_field_discriminator),
]

ResolvedNestedFields.model_rebuild()


class ResolvedFormat(FormatBase):
    """
    TODO
    """

    fields: list[ResolvedField] = Field(title="TODO", description="TODO")


class ResolvedDisplay(Model):
    """
    TODO
    """

    definitions: dict[str, ResolvedFieldDefinition] | None = Field(default=None, title="TODO", description="TODO")

    formats: dict[str, ResolvedFormat] = Field(title="TODO", description="TODO")
