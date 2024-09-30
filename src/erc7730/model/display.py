from enum import Enum
from typing import Annotated, Any, ForwardRef

from pydantic import Discriminator, RootModel, Tag
from pydantic import Field as PydanticField

from erc7730.model.base import Model
from erc7730.model.types import Id, Path

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


class FieldsParent(Model):
    path: str


class Reference(FieldsParent):
    ref: str = PydanticField(alias="$ref")
    params: dict[str, str] | None = None


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


class EnumParameters(Model):
    field_ref: str = PydanticField(alias="$ref")


def get_param_discriminator(v: Any) -> str | None:
    if isinstance(v, dict):
        if v.get("tokenPath") is not None:
            return "token_amount"
        if v.get("collectionPath") is not None:
            return "nft_name"
        if v.get("encoding") is not None:
            return "date"
        if v.get("base") is not None:
            return "unit"
        if v.get("$ref") is not None:
            return "enum"
        if v.get("type") is not None or v.get("sources") is not None:
            return "address_name"
        if v.get("selector") is not None or v.get("calleePath") is not None:
            return "call_data"
        return None
    if getattr(v, "tokenPath", None) is not None:
        return "token_amount"
    if getattr(v, "encoding", None) is not None:
        return "date"
    if getattr(v, "collectionPath", None) is not None:
        return "nft_name"
    if getattr(v, "base", None) is not None:
        return "unit"
    if getattr(v, "$ref", None) is not None:
        return "enum"
    if getattr(v, "type", None) is not None:
        return "address_name"
    if getattr(v, "selector", None) is not None:
        return "call_data"
    return None


FieldParameters = Annotated[
    Annotated[AddressNameParameters, Tag("address_name")]
    | Annotated[CallDataParameters, Tag("call_data")]
    | Annotated[TokenAmountParameters, Tag("token_amount")]
    | Annotated[NftNameParameters, Tag("nft_name")]
    | Annotated[DateParameters, Tag("date")]
    | Annotated[UnitParameters, Tag("unit")]
    | Annotated[EnumParameters, Tag("enum")],
    Discriminator(get_param_discriminator),
]


class FieldDescription(Model):
    id: Id | None = PydanticField(None, alias="$id")
    path: Path
    label: str
    format: FieldFormat | None
    params: FieldParameters | None = None


class NestedFields(FieldsParent):
    fields: list[ForwardRef("Field")] | None = None  # type: ignore


def get_discriminator_value(v: Any) -> str | None:
    if isinstance(v, dict):
        if v.get("label") is not None and v.get("format") is not None:
            return "field_description"
        if v.get("fields") is not None:
            return "nested_fields"
        if v.get("$ref") is not None:
            return "reference"
        return None
    if getattr(v, "label", None) is not None:
        return "field_description"
    if getattr(v, "fields", None) is not None:
        return "nested_fields"
    if getattr(v, "ref", None) is not None:
        return "reference"
    return None


class Field(
    RootModel[
        Annotated[
            Annotated[Reference, Tag("reference")]
            | Annotated[FieldDescription, Tag("field_description")]
            | Annotated[NestedFields, Tag("nested_fields")],
            Discriminator(get_discriminator_value),
        ]
    ]
):
    """Field"""


NestedFields.model_rebuild()


class Screen(RootModel[dict[str, Any]]):
    """Screen"""


class Format(Model):
    field_id: Id | None = PydanticField(None, alias="$id")
    intent: str | dict[str, str] | None = None
    fields: list[Field] | None = None
    required: list[str] | None = None
    screens: dict[str, list[Screen]] | None = None


class Display(Model):
    definitions: dict[str, FieldDescription] | None = None
    formats: dict[str, Format]
