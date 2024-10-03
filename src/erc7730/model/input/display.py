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


class InputReference(FieldsBase):
    """
    A reference to a shared definition that should be used as the field formatting definition.

    The value is the key in the display definitions section, as a path expression $.display.definitions.DEFINITION_NAME.
    It is used to share definitions between multiple messages / functions.
    """

    ref: str = Field(
        alias="$ref",
        title="Internal Definition",
        description="An internal definition that should be used as the field formatting definition. The value is the"
        "key in the display definitions section, as a path expression $.display.definitions.DEFINITION_NAME.",
    )

    params: dict[str, str] | None = Field(  # FIXME typing is wrong
        default=None,
        title="Parameters",
        description="Parameters override. These values takes precedence over the ones in the definition itself.",
    )


class InputEnumParameters(Model):
    """
    Enum Formatting Parameters.
    """

    ref: str = Field(
        alias="$ref",
        title="Enum reference",
        description="The internal path to the enum definition used to convert this value.",
    )


InputFieldParameters = Annotated[
    Annotated[AddressNameParameters, Tag("address_name")]
    | Annotated[CallDataParameters, Tag("call_data")]
    | Annotated[TokenAmountParameters, Tag("token_amount")]
    | Annotated[NftNameParameters, Tag("nft_name")]
    | Annotated[DateParameters, Tag("date")]
    | Annotated[UnitParameters, Tag("unit")]
    | Annotated[InputEnumParameters, Tag("enum")],
    Discriminator(field_parameters_discriminator),
]


class InputFieldDefinition(Model):
    """
    A field formatter, containing formatting information of a single field in a message.
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

    params: InputFieldParameters | None = Field(
        default=None,
        title="Format Parameters",
        description="Format specific parameters that are used to format the field value in a human readable way.",
    )


class InputFieldDescription(InputFieldDefinition, FieldsBase):
    """
    A field formatter, containing formatting information of a single field in a message.
    """


class InputNestedFields(FieldsBase):
    """
    A single set of field formats, allowing recursivity in the schema.

    Used to group whole definitions for structures for instance. This allows nesting definitions of formats, but note
    that support for deep nesting will be device dependent.
    """

    fields: list[ForwardRef("InputField")] = Field(  # type: ignore
        title="Fields", description="Nested fields formats."
    )


InputField = Annotated[
    Annotated[InputReference, Tag("reference")]
    | Annotated[InputFieldDescription, Tag("field_description")]
    | Annotated[InputNestedFields, Tag("nested_fields")],
    Discriminator(field_discriminator),
]


InputNestedFields.model_rebuild()


class InputFormat(FormatBase):
    """
    A structured data format specification, containing formatting information of fields in a single type of message.
    """

    fields: list[InputField] = Field(
        title="Field Formats set", description="An array containing the ordered definitions of fields formats."
    )


class InputDisplay(Model):
    """
    Display Formatting Info Section.
    """

    definitions: dict[str, InputFieldDefinition] | None = Field(
        default=None,
        title="Common Formatter Definitions",
        description="A set of definitions that can be used to share formatting information between multiple messages /"
        "functions. The definitions can be referenced by the key name in an internal path.",
    )

    formats: dict[str, InputFormat] = Field(
        title="List of field formats",
        description="The list includes formatting info for each field of a structure. This list is indexed by a key"
        "identifying uniquely the message's type in the abi. For smartcontracts, it is the selector of the"
        "function or its signature; and for EIP712 messages it is the primaryType of the message.",
    )
