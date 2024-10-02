from pydantic import AnyUrl, field_validator

from erc7730.model.base import Model
from erc7730.model.types import ContractAddress

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
    chainId: int
    address: ContractAddress


class Factory(Model):
    deployments: list[Deployment]
    deployEvent: str
