from enum import Enum
from typing import Any

from pydantic import Field as PydanticField
from pydantic import RootModel

from erc7730.model.base import Model
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class Source(str, Enum):
    WALLET = "wallet"
    ENS = "ens"
    CONTRACT = "contract"
    TOKEN = "token"  # nosec B105 - bandit false positive
    COLLECTION = "collection"


class FieldFormat(str, Enum):
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
    tokenPath: str
    nativeCurrencyAddress: str | None = None
    threshold: str | None = None
    message: str | None = None


class DateEncoding(str, Enum):
    BLOCKHEIGHT = "blockheight"
    TIMESTAMP = "timestamp"


class DateParameters(Model):
    encoding: DateEncoding


class AddressNameType(str, Enum):
    WALLET = "wallet"
    EOA = "eoa"
    CONTRACT = "contract"
    TOKEN = "token"  # nosec B105 - bandit false positive
    NFT = "nft"


class AddressNameSources(str, Enum):
    LOCAL = "local"
    ENS = "ens"


class AddressNameParameters(Model):
    type: AddressNameType | None = None
    sources: list[AddressNameSources] | None = None


class CallDataParameters(Model):
    selector: str | None = None
    calleePath: str | None = None


class NftNameParameters(Model):
    collectionPath: str


class UnitParameters(Model):
    base: str
    decimals: int | None = None
    prefix: bool | None = None


class Screen(RootModel[dict[str, Any]]):
    """Screen"""


class FieldsBase(Model):
    path: str


class FormatBase(Model):
    id: Id | None = PydanticField(None, alias="$id")
    intent: str | dict[str, str] | None = None
    required: list[str] | None = None
    screens: dict[str, list[Screen]] | None = None
