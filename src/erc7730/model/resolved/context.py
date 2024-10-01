from pydantic import AnyUrl, Field

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.context import Deployments, Domain, EIP712JsonSchema, Factory
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ResolvedEIP712(Model):
    domain: Domain | None = None
    schemas: list[EIP712JsonSchema]
    domainSeparator: str | None = None
    deployments: Deployments


class ResolvedEIP712DomainBinding(Model):
    eip712: ResolvedEIP712


class ResolvedContract(Model):
    abi: list[ABI]
    deployments: Deployments
    addressMatcher: AnyUrl | None = None
    factory: Factory | None = None


class ResolvedContractBinding(Model):
    contract: ResolvedContract


class ResolvedContractContext(ResolvedContractBinding):
    id: Id | None = Field(None, alias="$id")


class ResolvedEIP712Context(ResolvedEIP712DomainBinding):
    id: Id | None = Field(None, alias="$id")
