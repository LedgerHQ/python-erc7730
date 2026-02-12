"""
Object model for ERC-7730 v2 descriptors `display` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
"""

from typing import Annotated, Any, ForwardRef, Self

from pydantic import Discriminator, Field, Tag, model_validator

from erc7730.model.base import Model
from erc7730.model.display import (
    AddressNameType,
    FormatBase,
)
from erc7730.model.input.path import ContainerPathStr, DataPathStr, DescriptorPathStr
from erc7730.model.input.v2.format import DateEncoding, FieldFormat
from erc7730.model.input.v2.unions import (
    field_discriminator,
    field_parameters_discriminator,
    visibility_rules_discriminator,
)
from erc7730.model.types import HexStr, Id, MixedCaseAddress, ScalarType

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputVisibilityConditions(Model):
    """
    Complex visibility conditions for field display rules.
    """

    ifNotIn: list[str] | None = Field(
        None,
        title="If Not In",
        description="Display this field only if its value is NOT in this list.",
    )

    mustBe: list[str] | None = Field(
        None,
        title="Must Be",
        description="Skip displaying this field but its value MUST match one of these values.",
    )

    @model_validator(mode="after")
    def _validate_at_least_one_condition(self) -> Self:
        if self.ifNotIn is None and self.mustBe is None:
            raise ValueError('At least one of "ifNotIn" or "mustBe" must be set.')
        return self


InputVisibilityRules = Annotated[
    Annotated[str, Tag("simple")] | Annotated[InputVisibilityConditions, Tag("conditions")],
    Discriminator(visibility_rules_discriminator),
]


class InputMapReference(Model):
    """
    A reference to a map for dynamic value resolution.
    """

    map: DescriptorPathStr = Field(
        title="Map Reference",
        description="The path to the referenced map.",
    )

    keyPath: DescriptorPathStr | DataPathStr | ContainerPathStr = Field(
        title="Key Path",
        description="The path to the key used to resolve a value in the referenced map.",
    )


class InputFieldBase(Model):
    """
    A field formatter, containing formatting information of a single field in a message.
    """

    path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Path",
        description="A path to the field in the structured data. The path is a JSON path expression that can be used "
        """to extract the field value from the structured data. Exactly one of "path" or "value" must be set.""",
    )

    value: DescriptorPathStr | ScalarType | None = Field(
        default=None,
        title="Value",
        description="A literal value on which the format should be applied instead of looking up a field in the "
        """structured data. Exactly one of "path" or "value" must be set.""",
    )

    @model_validator(mode="after")
    def _validate_one_of_path_or_value(self) -> Self:
        if self.path is None and self.value is None:
            raise ValueError('Either "path" or "value" must be set.')
        if self.path is not None and self.value is not None:
            raise ValueError('"path" and "value" are mutually exclusive.')
        return self


class InputReference(InputFieldBase):
    """
    A reference to a shared definition that should be used as the field formatting definition.

    The value is the key in the display definitions section, as a path expression $.display.definitions.DEFINITION_NAME.
    It is used to share definitions between multiple messages / functions.
    """

    ref: DescriptorPathStr = Field(
        alias="$ref",
        title="Internal Definition",
        description="An internal definition that should be used as the field formatting definition. The value is the "
        "key in the display definitions section, as a path expression $.display.definitions.DEFINITION_NAME.",
    )

    params: dict[str, Any] | None = Field(
        default=None,
        title="Parameters",
        description="Parameters override. These values takes precedence over the ones in the definition itself.",
    )


class InputTokenAmountParameters(Model):
    """
    Token Amount Formatting Parameters.
    """

    tokenPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Token Path",
        description="Path reference to the address of the token contract. Used to associate correct ticker. If ticker "
        "is not found or tokenPath is not set, the wallet SHOULD display the raw value instead with an"
        '"Unknown token" warning. Exactly one of "tokenPath" or "token" must be set.',
    )

    token: DescriptorPathStr | MixedCaseAddress | InputMapReference | None = Field(
        default=None,
        title="Token",
        description=(
            "The address of the token contract, as constant value or map reference. "
            "Used to associate the correct ticker. If the ticker is not found or the value is not set, "
            'the wallet SHOULD display the raw value instead with an "Unknown token" warning. '
            'Exactly one of "tokenPath" or "token" must be set.'
        ),
    )

    nativeCurrencyAddress: list[DescriptorPathStr | MixedCaseAddress] | DescriptorPathStr | MixedCaseAddress | None = (
        Field(
            default=None,
            title="Native Currency Address",
            description="An address or array of addresses, any of which are interpreted as an amount in native "
            "currency rather than a token.",
        )
    )

    threshold: DescriptorPathStr | HexStr | int | None = Field(
        default=None,
        title="Unlimited Threshold",
        description="The threshold above which the amount should be displayed using the message parameter rather than "
        "the real amount (encoded as an int or byte array).",
    )

    message: DescriptorPathStr | str | None = Field(
        default=None,
        title="Unlimited Message",
        description="The message to display when the amount is above the threshold.",
    )

    chainId: int | DescriptorPathStr | InputMapReference | None = Field(
        default=None,
        title="Chain ID",
        description=(
            "Optional. The chain on which the token is deployed (constant, or a map reference). "
            "When present, the wallet SHOULD resolve token metadata (ticker, decimals) for this chain. "
            "Useful for cross-chain swap clear signing where the same token address may refer to different chains."
        ),
    )

    chainIdPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Chain ID Path",
        description=(
            "Optional. Path to the chain ID in the structured data. "
            "When present, the wallet SHOULD resolve token metadata for the chain at this path. "
            "Useful for cross-chain swap clear signing."
        ),
    )

    @model_validator(mode="after")
    def _validate_one_of_token_path_or_value(self) -> Self:
        if self.tokenPath is not None and self.token is not None:
            raise ValueError('"tokenPath" and "token" are mutually exclusive.')
        if self.chainId is not None and self.chainIdPath is not None:
            raise ValueError('"chainId" and "chainIdPath" are mutually exclusive.')
        return self


class InputAddressNameParameters(Model):
    """
    Address Names Formatting Parameters.
    """

    types: list[AddressNameType] | DescriptorPathStr | None = Field(
        default=None,
        title="Address Type",
        description="An array of expected types of the address. If set, the wallet SHOULD check that the address "
        "matches one of the types provided.",
        min_length=1,
    )

    sources: list[str] | DescriptorPathStr | None = Field(
        default=None,
        title="Trusted Sources",
        description="An array of acceptable sources for names. If set, the wallet SHOULD restrict name lookup to "
        "relevant sources.",
        min_length=1,
    )

    senderAddress: MixedCaseAddress | list[MixedCaseAddress] | DescriptorPathStr | InputMapReference | None = Field(
        default=None,
        title="Sender Address",
        description="Either a string or an array of strings. If the address pointed to by addressName is equal to one "
        "of the addresses in senderAddress, the addressName is interpreted as the sender referenced by @.from",
    )


class InputInteroperableAddressNameParameters(Model):
    """
    Interoperable Address Names Formatting Parameters.
    """

    types: list[str] | DescriptorPathStr | None = Field(
        default=None,
        title="Address Type",
        description="An array of expected types of the address (wallet, eoa, contract, token, collection).",
        min_length=1,
    )

    sources: list[str] | DescriptorPathStr | None = Field(
        default=None,
        title="Trusted Sources",
        description="An array of acceptable sources for names.",
        min_length=1,
    )

    senderAddress: MixedCaseAddress | list[MixedCaseAddress] | DescriptorPathStr | InputMapReference | None = Field(
        default=None,
        title="Sender Address",
        description="Either a string or an array of strings for sender address matching.",
    )


class InputCallDataParameters(Model):
    """
    Embedded Calldata Formatting Parameters.
    """

    calleePath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Callee Path",
        description="The path to the address of the contract being called by this embedded calldata. Exactly one of "
        '"calleePath" or "callee" must be set.',
    )

    callee: DescriptorPathStr | MixedCaseAddress | InputMapReference | None = Field(
        default=None,
        title="Callee",
        description=(
            "The address of the contract being called by this embedded calldata, "
            'as a constant value or map reference. Exactly one of "calleePath" or "callee" must be set.'
        ),
    )

    selectorPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Called Selector path",
        description="The path to selector being called, if not contained in the calldata. Only "
        'one of "selectorPath" or "selector" must be set.',
    )

    selector: DescriptorPathStr | str | InputMapReference | None = Field(
        default=None,
        title="Called Selector",
        description=(
            "The selector being called, if not contained in the calldata or provided as a map reference. "
            'Hex string representation. Only one of "selectorPath" or "selector" must be set.'
        ),
    )

    amountPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Amount path",
        description="The path to the amount being transferred, if not contained in the calldata. Only "
        'one of "amountPath" or "amount" must be set.',
    )

    amount: int | DescriptorPathStr | InputMapReference | None = Field(
        default=None,
        title="Amount",
        description="The amount being transferred, if not contained in the calldata or as map reference. Only "
        'one of "amountPath" or "amount" must be set.',
    )

    spenderPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Spender Path",
        description="The path to the spender, if not contained in the calldata. Only "
        'one of "spenderPath" or "spender" must be set.',
    )

    spender: DescriptorPathStr | MixedCaseAddress | InputMapReference | None = Field(
        default=None,
        title="Spender",
        description="the spender, if not contained in the calldata or as map reference. Only "
        'one of "spenderPath" or "spender" must be set.',
    )

    @model_validator(mode="after")
    def _validate_mutually_exclusive_path_or_value(self) -> Self:
        if self.calleePath is not None and self.callee is not None:
            raise ValueError('"calleePath" and "callee" are mutually exclusive.')
        if self.selectorPath is not None and self.selector is not None:
            raise ValueError('"selectorPath" and "selector" are mutually exclusive.')
        if self.amountPath is not None and self.amount is not None:
            raise ValueError('"amountPath" and "amount" are mutually exclusive.')
        if self.spenderPath is not None and self.spender is not None:
            raise ValueError('"spenderPath" and "spender" are mutually exclusive.')
        return self

    @model_validator(mode="after")
    def _validate_one_of_callee_path_or_value(self) -> Self:
        if self.calleePath is None and self.callee is None:
            raise ValueError('Either "calleePath" or "callee" must be set.')
        return self


class InputNftNameParameters(Model):
    """
    NFT Names Formatting Parameters.
    """

    collectionPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Collection Path",
        description="The path to the collection in the structured data. Exactly one of "
        '"collectionPath" or "collection" must be set.',
    )

    collection: DescriptorPathStr | MixedCaseAddress | InputMapReference | None = Field(
        default=None,
        title="Collection",
        description="The address of the collection contract, as a constant value or map reference. Exactly one of "
        '"collectionPath" or "collection" must be set.',
    )

    @model_validator(mode="after")
    def _validate_one_of_collection_path_or_value(self) -> Self:
        if self.collectionPath is None and self.collection is None:
            raise ValueError('Either "collectionPath" or "collection" must be set.')
        if self.collectionPath is not None and self.collection is not None:
            raise ValueError('"collectionPath" and "collection" are mutually exclusive.')
        return self


class InputDateParameters(Model):
    """
    Date Formatting Parameters
    """

    encoding: DateEncoding | DescriptorPathStr = Field(title="Date Encoding", description="The encoding of the date.")


class InputUnitParameters(Model):
    """
    Unit Formatting Parameters.
    """

    base: DescriptorPathStr | str = Field(
        title="Unit base symbol",
        description="The base symbol of the unit, displayed after the converted value. It can be an SI unit symbol or "
        "acceptable dimensionless symbols like % or bps.",
    )

    decimals: int | DescriptorPathStr | None = Field(
        default=None, title="Decimals", description="The number of decimals of the value, used to convert to a float."
    )

    prefix: bool | DescriptorPathStr | None = Field(
        default=None,
        title="Prefix",
        description="Whether the value should be converted to a prefixed unit, like k, M, G, etc.",
    )


class InputEnumParameters(Model):
    """
    Enum Formatting Parameters.
    """

    ref: DescriptorPathStr = Field(
        alias="$ref",
        title="Enum reference",
        description="The internal path to the enum definition used to convert this value.",
    )


class InputTokenTickerParameters(Model):
    """
    Token Ticker Formatting Parameters.
    """

    chainId: int | DescriptorPathStr | InputMapReference | None = Field(
        default=None,
        title="Chain ID",
        description=(
            "Optional. The chain on which the token is deployed (constant, or a map reference). "
            "When present, the wallet SHOULD resolve the token ticker for this chain. "
            "Useful for cross-chain swap clear signing."
        ),
    )

    chainIdPath: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Chain ID Path",
        description=(
            "Optional. Path to the chain ID in the structured data. "
            "When present, the wallet SHOULD resolve the token ticker for the chain at this path. "
            "Useful for cross-chain swap clear signing."
        ),
    )

    @model_validator(mode="after")
    def _validate_chainid_mutually_exclusive(self) -> Self:
        if self.chainId is not None and self.chainIdPath is not None:
            raise ValueError('"chainId" and "chainIdPath" are mutually exclusive.')
        return self


class InputEncryptionParameters(Model):
    """
    Encrypted Value Parameters.
    """

    scheme: str = Field(
        title="Encryption Scheme",
        description="The encryption scheme used to produce the handle.",
    )

    plaintextType: str | None = Field(
        default=None,
        title="Plaintext Type",
        description="Solidity type of the decrypted value (the handle does not encode this).",
    )

    fallbackLabel: str | None = Field(
        default=None,
        title="Fallback Label",
        description='Optional label to display when decryption is not possible. Defaults to "[Encrypted]".',
    )


# Extended field parameters for v2 - discriminator function needs to be updated
InputFieldParameters = Annotated[
    Annotated[InputAddressNameParameters, Tag("address_name")]
    | Annotated[InputInteroperableAddressNameParameters, Tag("interoperable_address_name")]
    | Annotated[InputCallDataParameters, Tag("call_data")]
    | Annotated[InputTokenAmountParameters, Tag("token_amount")]
    | Annotated[InputTokenTickerParameters, Tag("token_ticker")]
    | Annotated[InputNftNameParameters, Tag("nft_name")]
    | Annotated[InputDateParameters, Tag("date")]
    | Annotated[InputUnitParameters, Tag("unit")]
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
        description="An internal identifier that can be used either for clarity specifying what the element is or as a "
        "reference in device specific sections.",
    )

    label: DescriptorPathStr | str = Field(
        title="Field Label",
        description="The label of the field, that will be displayed to the user in front of the formatted field value.",
    )

    format: FieldFormat | None = Field(
        default=None,
        title="Field Format",
        description="The format of the field, that will be used to format the field value in a human readable way.",
    )

    params: InputFieldParameters | None = Field(
        default=None,
        title="Format Parameters",
        description="Format specific parameters that are used to format the field value in a human readable way.",
    )


class InputFieldDescription(InputFieldBase, InputFieldDefinition):
    """
    A field formatter, containing formatting information of a single field in a message.
    """

    visible: InputVisibilityRules | None = Field(
        default=None,
        title="Visibility Rules",
        description=(
            "Specifies when a field should be displayed based on its value or context. "
            "Defaults to 'always' if not specified."
        ),
    )

    separator: str | None = Field(
        default=None,
        title="Field Separator",
        description="Optional separator for array values with {index} interpolation support.",
    )

    encryption: InputEncryptionParameters | None = Field(
        default=None,
        title="Encryption Parameters",
        description=(
            "If present, the field value is encrypted. The format specifies how to display the decrypted value."
        ),
    )


class InputFieldGroup(Model):
    """
    A group of field formats, allowing recursivity in the schema and control over grouping and iteration.

    Used to group whole definitions for structures for instance. This allows nesting definitions of formats, but note
    that support for deep nesting will be device dependent.

    Unlike InputFieldBase, field groups do not require path or value (per v2 schema). The path is optional and there
    is no value field — field groups scope their children under the given path, or act as logical groupings when no
    path is provided.
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a "
        "reference in device specific sections.",
    )

    path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = Field(
        default=None,
        title="Path",
        description="An optional path to scope the field group under. When set, child fields are resolved relative to "
        "this path.",
    )

    label: str | None = Field(
        default=None,
        title="Group Label",
        description="An optional label for the field group.",
    )

    iteration: str | None = Field(
        default=None,
        title="Iteration Strategy",
        description="Specifies how iteration over arrays should be handled: 'sequential' or 'bundled'.",
    )

    fields: list[ForwardRef("InputField")] = Field(  # type: ignore
        title="Fields", description="Group of field formats."
    )


InputField = Annotated[
    Annotated[InputReference, Tag("reference")]
    | Annotated[InputFieldDescription, Tag("field_description")]
    | Annotated[InputFieldGroup, Tag("field_group")],
    Discriminator(field_discriminator),
]


class InputFormat(FormatBase):
    """
    A structured data format specification containing formatting information of fields
    in a single type of message (v2).
    """

    interpolatedIntent: str | None = Field(
        default=None,
        title="Interpolated Intent Message",
        description=(
            "An optional intent string with embedded field values using {path} interpolation syntax. "
            "This provides a dynamic, contextual description by embedding actual transaction or message "
            "values directly in the intent string."
        ),
    )

    fields: list[InputField] = Field(
        title="Field Formats set",
        description="An array containing the ordered definitions of fields formats.",
    )

    # Note: v2 removed required and excluded arrays


class InputDisplay(Model):
    """
    Display Formatting Info Section (v2).
    """

    definitions: dict[str, InputFieldDefinition] | None = Field(
        default=None,
        title="Common Formatter Definitions",
        description="A set of definitions that can be used to share formatting information between multiple messages / "
        "functions. The definitions can be referenced by the key name in an internal path.",
    )

    formats: dict[str, InputFormat] = Field(
        title="List of field formats",
        description="The list includes formatting info for each field of a structure. This list is indexed by a key "
        "identifying uniquely the message's type in the abi. For smartcontracts, it is the selector of the "
        "function or its signature; and for EIP712 messages it is the primaryType of the message.",
    )
