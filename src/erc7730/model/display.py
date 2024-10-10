from enum import Enum
from typing import Annotated, Any

from pydantic import Field, RootModel

from erc7730.model.base import Model
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class FieldFormat(str, Enum):
    """
    The format of the field, that will be used to format the field value in a human readable way.
    """

    RAW = "raw"
    """The field should be displayed as the natural representation of the underlying structured data type."""

    ADDRESS_NAME = "addressName"
    """The field should be displayed as a trusted name, or as a raw address if no names are found in trusted sources.
    List of trusted sources can be optionally specified in parameters."""

    CALL_DATA = "calldata"
    """The field is itself a calldata embedded in main call. Another ERC 7730 should be used to parse this field. If not
    available or not supported, the wallet MAY display a hash of the embedded calldata instead."""

    AMOUNT = "amount"
    """The field should be displayed as an amount in underlying currency, converted using the best magnitude / ticker
    available."""

    TOKEN_AMOUNT = "tokenAmount"  # nosec B105 - bandit false positive
    """The field should be displayed as an amount, preceded by the ticker. The magnitude and ticker should be derived
    from the tokenPath parameter corresponding metadata."""

    NFT_NAME = "nftName"
    """The field should be displayed as a single NFT names, or as a raw token Id if a specific name is not found.
    Collection is specified by the collectionPath parameter."""

    DATE = "date"
    """The field should be displayed as a date. Suggested RFC3339 representation. Parameter specifies the encoding of
    the date."""

    DURATION = "duration"
    """The field should be displayed as a duration in HH:MM:ss form. Value is interpreted as a number of seconds."""

    UNIT = "unit"
    """The field should be displayed as a percentage. Magnitude of the percentage encoding is specified as a parameter.
    Example: a value of 3000 with magnitude 4 is displayed as 0.3%."""

    ENUM = "enum"
    """The field should be displayed as a human readable string by converting the value using the enum referenced in
    parameters."""


class TokenAmountParameters(Model):
    """
    Token Amount Formatting Parameters.
    """

    tokenPath: str | None = Field(
        title="Token Path",
        description="Path reference to the address of the token contract. Used to associate correct ticker. If ticker"
        "is not found or tokenPath is not set, the wallet SHOULD display the raw value instead with an"
        '"Unknown token" warning.',
    )

    nativeCurrencyAddress: str | list[str] | None = Field(
        default=None,
        title="Native Currency Address",
        description="An address or array of addresses, any of which are interpreted as an amount in native currency"
        "rather than a token.",
    )

    threshold: str | None = Field(
        default=None,
        title="Unlimited Threshold",
        description="The threshold above which the amount should be displayed using the message parameter rather than"
        "the real amount.",
    )

    message: str | None = Field(
        default=None,
        title="Unlimited Message",
        description="The message to display when the amount is above the threshold.",
    )


class DateEncoding(str, Enum):
    """
    The encoding for a date.
    """

    BLOCKHEIGHT = "blockheight"
    """The date is encoded as a block height."""

    TIMESTAMP = "timestamp"
    """The date is encoded as a timestamp."""


class DateParameters(Model):
    """
    Date Formatting Parameters
    """

    encoding: DateEncoding = Field(title="Date Encoding", description="The encoding of the date.")


class AddressNameType(str, Enum):
    """
    The type of address to display. Restrict allowable sources of names and MAY lead to additional checks from wallets.
    """

    WALLET = "wallet"
    """Address is an account controlled by the wallet."""

    EOA = "eoa"
    """Address is an Externally Owned Account."""

    CONTRACT = "contract"
    """Address is a well known smartcontract."""

    TOKEN = "token"  # nosec B105 - bandit false positive
    """Address is a well known ERC-20 token."""

    COLLECTION = "collection"
    """Address is a well known NFT collection."""


class AddressNameSources(str, Enum):
    """
    Trusted Source for names.
    """

    LOCAL = "local"
    """Address MAY be replaced with a local name trusted by user. Wallets MAY consider that local setting for sources
    is always valid."""

    ENS = "ens"
    """Address MAY be replaced with an associated ENS domain."""


class AddressNameParameters(Model):
    """
    Address Names Formatting Parameters.
    """

    type: AddressNameType | None = Field(
        default=None,
        title="Address Type",
        description="The type of address to display. Restrict allowable sources of names and MAY lead to additional"
        "checks from wallets.",
    )

    sources: list[AddressNameSources] | None = Field(
        default=None,
        title="Trusted Sources",
        description="Trusted Sources for names, in order of preferences. See specification for more details on sources"
        "values.",
    )


class CallDataParameters(Model):
    """
    Embedded Calldata Formatting Parameters.
    """

    selector: str | None = Field(
        default=None,
        title="Called Selector",
        description="The selector being called, if not contained in the calldata. Hex string representation.",
    )

    calleePath: str | None = Field(
        default=None,
        title="Callee Path",
        description="The path to the address of the contract being called by this embedded calldata.",
    )


class NftNameParameters(Model):
    """
    NFT Names Formatting Parameters.
    """

    collectionPath: str = Field(
        title="Collection Path", description="The path to the collection in the structured data."
    )


class UnitParameters(Model):
    """
    Unit Formatting Parameters.
    """

    base: str = Field(
        title="Unit base symbol",
        description="The base symbol of the unit, displayed after the converted value. It can be an SI unit symbol or"
        "acceptable dimensionless symbols like % or bps.",
    )

    decimals: int | None = Field(
        default=None, title="Decimals", description="The number of decimals of the value, used to convert to a float."
    )

    prefix: bool | None = Field(
        default=None,
        title="Prefix",
        description="Whether the value should be converted to a prefixed unit, like k, M, G, etc.",
    )


class Screen(RootModel[dict[str, Any]]):
    """
    Screens section is used to group multiple fields to display into screens. Each key is a wallet type name. The
    format of the screens is wallet type dependent, as well as what can be done (reordering fields, max number of
    screens, etc...). See each wallet manufacturer documentation for more information.
    """


class FieldsBase(Model):
    """
    A field formatter, containing formatting information of a single field in a message.
    """

    path: str = Field(
        title="Path",
        description="A path to the field in the structured data. The path is a JSON path expression that can be used to"
        "extract the field value from the structured data.",
    )


SimpleIntent = Annotated[
    str,
    Field(
        title="Simple Intent",
        description="A description of the intent of the structured data signing, that will be displayed to the user.",
    ),
]

ComplexIntent = Annotated[
    dict[str, str],
    Field(
        title="Complex Intent",
        description="A description of the intent of the structured data signing, that will be displayed to the user.",
    ),
]


class FormatBase(Model):
    """
    A structured data format specification, containing formatting information of fields in a single type of message.
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    intent: SimpleIntent | ComplexIntent | None = Field(
        default=None,
        title="Intent Message",
        description="A description of the intent of the structured data signing, that will be displayed to the user.",
    )

    required: list[str] | None = Field(
        default=None,
        title="Required fields",
        description="A list of fields that are required to be displayed to the user. A field that has a formatter and"
        "is not in this list is optional. A field that does not have a formatter should be silent, ie not"
        "shown.",
    )

    excluded: list[str] | None = Field(
        default=None,
        title="Excluded fields",
        description="Intentionally excluded fields, as an array of *paths* referring to specific fields. A field that "
        "has no formatter and is not declared in this list MAY be considered as an error by the wallet when"
        "interpreting the descriptor.",
    )

    screens: dict[str, list[Screen]] | None = Field(
        default=None,
        title="Screens grouping information",
        description="Screens section is used to group multiple fields to display into screens. Each key is a wallet"
        "type name. The format of the screens is wallet type dependent, as well as what can be done (reordering"
        "fields, max number of screens, etc...). See each wallet manufacturer documentation for more"
        "information.",
    )
