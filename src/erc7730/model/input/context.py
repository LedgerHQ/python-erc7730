from pydantic import AnyUrl, Field

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.context import Deployment, Domain, EIP712JsonSchema, Factory
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputContract(Model):
    abi: list[ABI] | AnyUrl
    deployments: list[Deployment]
    addressMatcher: AnyUrl | None = None
    factory: Factory | None = None


class InputEIP712(Model):
    domain: Domain | None = None
    schemas: list[EIP712JsonSchema | AnyUrl]
    domainSeparator: str | None = None
    deployments: list[Deployment]


class InputContractContext(Model):
    id: Id | None = Field(None, alias="$id")
    contract: InputContract


class InputEIP712Context(Model):
    id: Id | None = Field(None, alias="$id")
    eip712: InputEIP712
