from pydantic import AnyUrl, Field

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.context import Deployment, Domain, EIP712JsonSchema, Factory
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ResolvedContract(Model):
    abi: list[ABI]
    deployments: list[Deployment]
    addressMatcher: AnyUrl | None = None
    factory: Factory | None = None


class ResolvedEIP712(Model):
    domain: Domain | None = None
    schemas: list[EIP712JsonSchema]
    domainSeparator: str | None = None
    deployments: list[Deployment]


class ResolvedContractContext(Model):
    id: Id | None = Field(None, alias="$id")
    contract: ResolvedContract


class ResolvedEIP712Context(Model):
    id: Id | None = Field(None, alias="$id")
    eip712: ResolvedEIP712
