from erc7730.model.base import BaseLibraryModel
from erc7730.model.types import Id, Path
from typing import Annotated, Any, Dict, ForwardRef, Optional, Union
from enum import Enum
from pydantic import Discriminator, RootModel, Field as PydanticField, Tag


class Source(str, Enum):
    WALLET = "wallet"
    ENS = "ens"
    CONTRACT = "contract"
    TOKEN = "token"
    COLLECTION = "collection"


class FieldFormat(str, Enum):
    RAW = "raw"
    ADDRESS_NAME = "addressName"
    CALL_DATA = "calldata"
    AMOUNT = "amount"
    TOKEN_AMOUNT = "tokenAmount"
    NFT_NAME = "nftName"
    DATE = "date"
    DURATION = "duration"
    UNIT = "unit"
    ENUM = "enum"


class FieldsParent(BaseLibraryModel):
    path: str


class Reference(FieldsParent):
    ref: str = PydanticField(alias="$ref")
    params: Optional[dict[str, str]] = None


class TokenAmountParameters(BaseLibraryModel):
    tokenPath: str
    nativeCurrencyAddress: Optional[str] = None
    threshold: Optional[str] = None
    message: Optional[str] = None


class DateEncoding(str, Enum):
    BLOCKHEIGHT = "blockheight"
    TIMESTAMP = "timestamp"


class DateParameters(BaseLibraryModel):
    encoding: DateEncoding


class AddressNameType(str, Enum):
    WALLET = "wallet"
    EOA = "eoa"
    CONTRACT = "contract"
    TOKEN = "token"
    NFT = "nft"


class AddressNameSources(str, Enum):
    LOCAL = "local"
    ENS = "ens"


class AddressNameParameters(BaseLibraryModel):
    type: Optional[AddressNameType] = None
    sources: Optional[list[AddressNameSources]] = None


class CallDataParameters(BaseLibraryModel):
    selector: Optional[str] = None
    calleePath: Optional[str] = None


class NftNameParameters(BaseLibraryModel):
    collectionPath: str


class UnitParameters(BaseLibraryModel):
    base: str
    decimals: Optional[int] = None
    prefix: Optional[bool] = None


class EnumParameters(BaseLibraryModel):
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


class FieldDescription(BaseLibraryModel):
    path: Optional[Path] = None
    field_id: Optional[Id] = PydanticField(None, alias="$id")
    label: str
    format: Optional[FieldFormat]
    params: Optional[
        Annotated[
            Union[
                Annotated[AddressNameParameters, Tag("address_name")],
                Annotated[CallDataParameters, Tag("call_data")],
                Annotated[TokenAmountParameters, Tag("token_amount")],
                Annotated[NftNameParameters, Tag("nft_name")],
                Annotated[DateParameters, Tag("date")],
                Annotated[UnitParameters, Tag("unit")],
                Annotated[EnumParameters, Tag("enum")],
            ],
            Discriminator(get_param_discriminator),
        ]
    ] = None


class NestedFields(FieldsParent):
    fields: Optional[list[ForwardRef("Field")]] = None  # type: ignore


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
            Union[
                Annotated[Reference, Tag("reference")],
                Annotated[FieldDescription, Tag("field_description")],
                Annotated[NestedFields, Tag("nested_fields")],
            ],
            Discriminator(get_discriminator_value),
        ]
    ]
):
    """Field"""


NestedFields.model_rebuild()


class Screen(RootModel[dict[str, Any]]):
    """Screen"""


class Format(BaseLibraryModel):
    field_id: Optional[Id] = PydanticField(None, alias="$id")
    intent: Optional[Union[str, Dict[str, str]]] = None
    fields: Optional[list[Field]] = None
    required: Optional[list[str]] = None
    screens: Optional[dict[str, list[Screen]]] = None


class Display(BaseLibraryModel):
    definitions: Optional[dict[str, FieldDescription]] = None
    formats: dict[str, Format]
