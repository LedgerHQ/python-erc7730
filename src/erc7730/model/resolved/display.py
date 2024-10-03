from typing import Annotated, ForwardRef

from pydantic import Discriminator, Field, Tag

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
from erc7730.model.unions import field_discriminator, field_parameters_discriminator

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ResolvedEnumParameters(Model):
    """
    Enum Formatting Parameters.
    """

    ref: str = Field(alias="$ref")  # TODO must be inlined here


ResolvedFieldParameters = Annotated[
    Annotated[AddressNameParameters, Tag("address_name")]
    | Annotated[CallDataParameters, Tag("call_data")]
    | Annotated[TokenAmountParameters, Tag("token_amount")]
    | Annotated[NftNameParameters, Tag("nft_name")]
    | Annotated[DateParameters, Tag("date")]
    | Annotated[UnitParameters, Tag("unit")]
    | Annotated[ResolvedEnumParameters, Tag("enum")],
    Discriminator(field_parameters_discriminator),
]


class ResolvedFieldDefinition(Model):
    """
    TODO this should be removed from the resolved state and only have ResolvedFieldDescription
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

    format: FieldFormat | None = Field(
        title="Field Format",
        description="The format of the field, that will be used to format the field value in a human readable way.",
    )

    params: ResolvedFieldParameters | None = Field(
        default=None,
        title="Format Parameters",
        description="Format specific parameters that are used to format the field value in a human readable way.",
    )


class ResolvedFieldDescription(ResolvedFieldDefinition, FieldsBase):
    """
    A field formatter, containing formatting information of a single field in a message.
    """


class ResolvedNestedFields(FieldsBase):
    """
    A single set of field formats, allowing recursivity in the schema.

    Used to group whole definitions for structures for instance. This allows nesting definitions of formats, but note
    that support for deep nesting will be device dependent.
    """

    fields: list[ForwardRef("ResolvedField")] = Field(  # type: ignore
        title="Fields", description="Nested fields formats."
    )


ResolvedField = Annotated[
    Annotated[ResolvedFieldDescription, Tag("field_description")]
    | Annotated[ResolvedNestedFields, Tag("nested_fields")],
    Discriminator(field_discriminator),
]

ResolvedNestedFields.model_rebuild()


class ResolvedFormat(FormatBase):
    """
    A structured data format specification, containing formatting information of fields in a single type of message.
    """

    fields: list[ResolvedField] = Field(
        title="Field Formats set", description="An array containing the ordered definitions of fields formats."
    )


class ResolvedDisplay(Model):
    """
    Display Formatting Info Section.
    """

    # FIXME there should be no definitions anymore in resolved state
    definitions: dict[str, ResolvedFieldDefinition] | None = Field(
        default=None,
        title="Common Formatter Definitions",
        description="A set of definitions that can be used to share formatting information between multiple messages /"
        "functions. The definitions can be referenced by the key name in an internal path.",
    )

    formats: dict[str, ResolvedFormat] = Field(
        title="List of field formats",
        description="The list includes formatting info for each field of a structure. This list is indexed by a key"
        "identifying uniquely the message's type in the abi. For smartcontracts, it is the selector of the"
        "function or its signature; and for EIP712 messages it is the primaryType of the message.",
    )
