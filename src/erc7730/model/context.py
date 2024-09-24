from enum import Enum
from typing import ForwardRef, Union, Optional
from pydantic import AnyUrl, RootModel, field_validator, Field
from erc7730.model.base import BaseLibraryModel
from erc7730.model.types import ContractAddress, Id


class NameType(BaseLibraryModel):
    name: str
    type: str


class EIP712JsonSchema(BaseLibraryModel):
    primaryType: str
    types: dict[str, list[NameType]]

    @field_validator("types")
    @classmethod
    def validate_types(cls, value: dict[str, list[NameType]]) -> dict[str, list[NameType]]:
        # validate that EIP712Domain with expected values
        return value


class EIP712Schema(BaseLibraryModel):
    eip712Schema: Union[AnyUrl, EIP712JsonSchema]


class Domain(BaseLibraryModel):
    name: Optional[str] = None
    version: Optional[str] = None
    chainId: Optional[int] = None
    verifyingContract: Optional[ContractAddress] = None


class Deployment(BaseLibraryModel):
    chainId: Optional[int] = None
    address: Optional[str] = None


class Deployments(RootModel[list[Deployment]]):
    """deployments"""


class EIP712(BaseLibraryModel):
    domain: Optional[Domain] = None
    schemas: Optional[list[Union[EIP712JsonSchema, AnyUrl]]] = None
    domainSeparator: Optional[str] = None
    deployments: Optional[Deployments] = None


class EIP712DomainBinding(BaseLibraryModel):
    eip712: EIP712


class AbiParameter(BaseLibraryModel):
    name: str
    type: str
    internalType: Optional[str] = None
    components: Optional[list[ForwardRef("AbiParameter")]] = None  # type: ignore


AbiParameter.model_rebuild()


class StateMutability(Enum):
    pure = "pure"
    view = "view"
    nonpayable = "nonpayable"
    payable = "payable"


class Type(Enum):
    function = "function"
    constructor = "constructor"
    receive = "receive"
    fallback = "fallback"


class AbiJsonSchemaItem(BaseLibraryModel):
    name: str
    inputs: list[AbiParameter]
    outputs: Optional[list[AbiParameter]]
    stateMutability: Optional[StateMutability] = None
    type: Type
    constant: bool | None = None
    payable: bool | None = None


class AbiJsonSchema(RootModel[list[AbiJsonSchemaItem]]):
    """abi json schema"""


class Factory(BaseLibraryModel):
    deployments: Deployments
    deployEvent: str


class Contract(BaseLibraryModel):
    abi: Optional[Union[AnyUrl, AbiJsonSchema]] = None
    deployments: Optional[Deployments] = None
    addressMatcher: Optional[AnyUrl] = None
    factory: Optional[Factory] = None


class ContractBinding(BaseLibraryModel):
    contract: Contract


class ContractContext(ContractBinding):
    id: Optional[Id] = Field(None, alias="$id")


class EIP712Context(EIP712DomainBinding):
    id: Optional[Id] = Field(None, alias="$id")
