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


InputField = Annotated[
    Annotated[InputReference, Tag("reference")]
    | Annotated[InputFieldDescription, Tag("field_description")]
    | Annotated[InputNestedFields, Tag("nested_fields")],
    Discriminator(field_discriminator),
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
