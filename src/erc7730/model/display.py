from enum import Enum
from typing import Any

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
    TODO
    """

    RAW = "raw"
    ADDRESS_NAME = "addressName"
    CALL_DATA = "calldata"
    AMOUNT = "amount"
    TOKEN_AMOUNT = "tokenAmount"  # nosec B105 - bandit false positive
    NFT_NAME = "nftName"
    DATE = "date"
    DURATION = "duration"
    UNIT = "unit"
    ENUM = "enum"


class TokenAmountParameters(Model):
    """
    Token Amount Formatting Parameters.
    """

    tokenPath: str = Field(title="Token Path", description="The path to the token address in the structured data, or in the ERC 7730 file.")

    nativeCurrencyAddress: str | None = Field(default=None, title="Native Currency Address", description="An address equal to this value is interpreted as an amount in native currency rather than a token.")

    threshold: str | None = Field(default=None, title="Unlimited Threshold", description="The threshold above which the amount should be displayed using the message parameter rather than the real amount.")

    message: str | None = Field(default=None, title="Unlimited Message", description="The message to display when the amount is above the threshold.")


class DateEncoding(str, Enum):
    """
    The encoding for a date.
    """

    BLOCKHEIGHT = "blockheight"
    TIMESTAMP = "timestamp"


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
    TODO
    """

    type: AddressNameType | None = Field(default=None, title="TODO", description="TODO")

    sources: list[AddressNameSources] | None = Field(default=None, title="TODO", description="TODO")


class CallDataParameters(Model):
    """
    TODO
    """

    selector: str | None = Field(default=None, title="TODO", description="TODO")

    calleePath: str | None = Field(default=None, title="TODO", description="TODO")


class NftNameParameters(Model):
    """
    NFT Names Formatting Parameters.
    """

    collectionPath: str = Field(title="Collection Path", description="The path to the collection in the structured data.")


class UnitParameters(Model):
    """
    TODO
    """

    base: str = Field(title="TODO", description="TODO")

    decimals: int | None = Field(default=None, title="TODO", description="TODO")

    prefix: bool | None = Field(default=None, title="TODO", description="TODO")


class Screen(RootModel[dict[str, Any]]):
    """
    TODO
    """


class FieldsBase(Model):
    """
    TODO
    """

    path: str = Field(title="TODO", description="TODO")


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

    intent: str | dict[str, str] | None = Field(default=None, title="TODO", description="TODO")

    required: list[str] | None = Field(default=None, title="TODO", description="TODO")

    screens: dict[str, list[Screen]] | None = Field(default=None, title="TODO", description="TODO")
