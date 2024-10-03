from enum import Enum
from typing import Annotated, Any

from pydantic import Field, RootModel

from erc7730.model.base import Model
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class Source(str, Enum):
    """
    TODO
    """

    WALLET = "wallet"
    ENS = "ens"
    CONTRACT = "contract"
    TOKEN = "token"  # nosec B105 - bandit false positive
    COLLECTION = "collection"


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

    tokenPath: str = Field(
        title="Token Path", description="The path to the token address in the structured data, or in the ERC 7730 file."
    )

    nativeCurrencyAddress: str | None = Field(
        default=None,
        title="Native Currency Address",
        description="An address equal to this value is interpreted as an amount in native currency rather than a"
        "token.",
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
    TODO
    """

    WALLET = "wallet"
    EOA = "eoa"
    CONTRACT = "contract"
    TOKEN = "token"  # nosec B105 - bandit false positive
    NFT = "nft"


class AddressNameSources(str, Enum):
    """
    TODO
    """

    LOCAL = "local"
    ENS = "ens"


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
        title="TODO",
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
    TODO
    """

    path: str = Field(title="TODO", description="TODO")


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
    TODO
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

    screens: dict[str, list[Screen]] | None = Field(
        default=None,
        title="Screens grouping information",
        description="Screens section is used to group multiple fields to display into screens. Each key is a wallet"
        "type name. The format of the screens is wallet type dependent, as well as what can be done (reordering"
        "fields, max number of screens, etc...). See each wallet manufacturer documentation for more"
        "information.",
    )
