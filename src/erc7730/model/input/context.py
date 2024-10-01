from pydantic import AnyUrl, Field

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.context import Deployments, Domain, EIP712JsonSchema, Factory
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputEIP712(Model):
    domain: Domain | None = None
    schemas: list[EIP712JsonSchema | AnyUrl]
    domainSeparator: str | None = None
    deployments: Deployments


class InputEIP712DomainBinding(Model):
    eip712: InputEIP712


class InputContract(Model):
    abi: AnyUrl | list[ABI]
    deployments: Deployments
    addressMatcher: AnyUrl | None = None
    factory: Factory | None = None


class InputContractBinding(Model):
    contract: InputContract


class InputContractContext(InputContractBinding):
    id: Id | None = Field(None, alias="$id")


class InputEIP712Context(InputEIP712DomainBinding):
    id: Id | None = Field(None, alias="$id")
