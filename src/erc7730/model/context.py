from enum import Enum
from typing import ForwardRef

from pydantic import AnyUrl, Field, RootModel, field_validator

from erc7730.model.base import Model
from erc7730.model.types import ContractAddress, Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class NameType(Model):
    name: str
    type: str


class EIP712JsonSchema(Model):
    primaryType: str
    types: dict[str, list[NameType]]

    @classmethod
    @field_validator("types")
    def validate_types(cls, value: dict[str, list[NameType]]) -> dict[str, list[NameType]]:
        # TODO validate that EIP712Domain matches with expected values
        return value


class EIP712Schema(Model):
    eip712Schema: AnyUrl | EIP712JsonSchema


class Domain(Model):
    name: str | None = None
    version: str | None = None
    chainId: int | None = None
    verifyingContract: ContractAddress | None = None


class Deployment(Model):
    chainId: int | None = None
    address: str | None = None


class Deployments(RootModel[list[Deployment]]):
    """deployments"""


class EIP712(Model):
    domain: Domain | None = None
    schemas: list[EIP712JsonSchema | AnyUrl] | None = None
    domainSeparator: str | None = None
    deployments: Deployments | None = None


class EIP712DomainBinding(Model):
    eip712: EIP712


class AbiParameter(Model):
    name: str
    type: str
    internalType: str | None = None
    components: list[ForwardRef("AbiParameter")] | None = None  # type: ignore


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


class AbiJsonSchemaItem(Model):
    name: str
    inputs: list[AbiParameter]
    outputs: list[AbiParameter] | None
    stateMutability: StateMutability | None = None
    type: Type
    constant: bool | None = None
    payable: bool | None = None


class AbiJsonSchema(RootModel[list[AbiJsonSchemaItem]]):
    """abi json schema"""


class Factory(Model):
    deployments: Deployments
    deployEvent: str


class Contract(Model):
    abi: AnyUrl | AbiJsonSchema | None = None
    deployments: Deployments | None = None
    addressMatcher: AnyUrl | None = None
    factory: Factory | None = None


class ContractBinding(Model):
    contract: Contract


class ContractContext(ContractBinding):
    id: Id | None = Field(None, alias="$id")


class EIP712Context(EIP712DomainBinding):
    id: Id | None = Field(None, alias="$id")
