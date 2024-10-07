from typing import Annotated

from pydantic import AnyUrl, Field

from erc7730.model.base import Model
from erc7730.model.types import ContractAddress

# ruff: noqa: N815 - camel case field names are tolerated to match schema


EIP712Type = Annotated[
    str, Field(title="EIP12 Type Identifier", description="An EIP-712 scalar or structured type identifier.")
]


class EIP712Field(Model):
    """
    EIP-712 field, which is a tuple of a name and a type.
    """

    name: str = Field(title="Name", description="The EIP-712 field name.")

    type: EIP712Type = Field(title="Type", description="The EIP-712 field type identifier.")


class EIP712JsonSchema(Model):
    """
    EIP-712 message schema.
    """

    primaryType: EIP712Type = Field(title="Primary Type", description="The identifier of the schema primary type.")

    types: dict[EIP712Type, list[EIP712Field]] = Field(
        title="Types", description="The schema types reachable from primary type."
    )


class EIP712Schema(Model):
    """
    EIP-712 message schema.
    """

    eip712Schema: AnyUrl | EIP712JsonSchema = Field(
        title="EIP-712 message schema", description="The EIP-712 message schema."
    )


class Domain(Model):
    """
    EIP 712 Domain Binding constraint.

    Each value of the domain constraint MUST match the corresponding eip 712 message domain value.
    """

    name: str | None = Field(default=None, title="Name", description="The EIP-712 domain name.")

    version: str | None = Field(default=None, title="Version", description="The EIP-712 version.")

    chainId: int | None = Field(default=None, title="Chain ID", description="The EIP-155 chain id.")

    verifyingContract: ContractAddress | None = Field(
        default=None, title="Verifying Contract", description="The EIP-712 verifying contract address."
    )


class Deployment(Model):
    """
    A deployment describing where the contract is deployed.

    The target contract (Tx to or factory) MUST match one of those deployments.
    """

    chainId: int = Field(title="Chain ID", description="The deployment EIP-155 chain id.")

    address: ContractAddress = Field(title="Contract Address", description="The deployment contract address.")


class Factory(Model):
    """
    A factory constraint is used to check whether the target contract is deployed by a specified factory.
    """

    deployments: list[Deployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
    )

    deployEvent: str = Field(
        title="Deploy Event signature",
        description="The event signature that the factory emits when deploying a new contract.",
    )


class BindingContext(Model):
    deployments: list[Deployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
    )
