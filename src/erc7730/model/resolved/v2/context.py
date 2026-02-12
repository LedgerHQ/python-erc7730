"""
Object model for ERC-7730 v2 resolved descriptors `context` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
"""

from pydantic import Field

from erc7730.model.base import Model
from erc7730.model.types import Address, Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class ResolvedDomain(Model):
    """
    EIP 712 Domain Binding constraint (resolved).

    Each value of the domain constraint MUST match the corresponding eip 712 message domain value.
    """

    name: str | None = Field(default=None, title="Name", description="The EIP-712 domain name.")

    version: str | None = Field(default=None, title="Version", description="The EIP-712 version.")

    chainId: int | None = Field(default=None, title="Chain ID", description="The EIP-155 chain id.")

    verifyingContract: Address | None = Field(
        default=None,
        title="Verifying Contract",
        description="The EIP-712 verifying contract address (normalized to lowercase).",
    )


class ResolvedDeployment(Model):
    """
    A deployment describing where the contract is deployed (resolved).

    The target contract (Tx to or factory) MUST match one of those deployments.
    """

    chainId: int = Field(title="Chain ID", description="The deployment EIP-155 chain id.")

    address: Address = Field(
        title="Contract Address", description="The deployment contract address (normalized to lowercase)."
    )


class ResolvedFactory(Model):
    """
    A factory constraint is used to check whether the target contract is deployed by a specified factory (resolved).
    """

    deployments: list[ResolvedDeployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
    )

    deployEvent: str = Field(
        title="Deploy Event signature",
        description="The event signature that the factory emits when deploying a new contract.",
    )


class ResolvedBindingContext(Model):
    deployments: list[ResolvedDeployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
        min_length=1,
    )


class ResolvedContract(ResolvedBindingContext):
    """
    The contract binding context is a set constraints that are used to bind the ERC7730 file to a specific smart
    contract (resolved).
    """

    # ABI is deprecated, so dropped from resolved model.

    addressMatcher: str | None = Field(
        None,
        title="Address Matcher",
        description="A resolved address matcher that should be used to match the contract address.",
    )

    factory: ResolvedFactory | None = Field(
        None,
        title="Factory Constraint",
        description="A factory constraint is used to check whether the target contract is deployed by a specified"
        "factory.",
    )


class ResolvedEIP712(ResolvedBindingContext):
    """
    EIP 712 Binding (resolved).

    The EIP-712 binding context is a set of constraints that must be verified by the message being signed.
    """

    domain: ResolvedDomain | None = Field(
        default=None,
        title="EIP 712 Domain Binding constraint",
        description="Each value of the domain constraint MUST match the corresponding eip 712 message domain value.",
    )

    domainSeparator: str | None = Field(
        default=None,
        title="Domain Separator constraint",
        description="The domain separator value that must be matched by the message. In hex string representation.",
    )

    # Schemas are deprecated, so dropped from resolved model.


class ResolvedContractContext(Model):
    """
    Contract Binding Context (resolved).

    The contract binding context is a set constraints that are used to bind the ERC7730 file to a specific smart
    contract.
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    contract: ResolvedContract = Field(
        title="Contract Binding Context",
        description="The contract binding context is a set constraints that are used to bind the ERC7730 file to a"
        "specific smart contract.",
    )


class ResolvedEIP712Context(Model):
    """
    EIP 712 Binding (resolved).

    The EIP-712 binding context is a set of constraints that must be verified by the message being signed.
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    eip712: ResolvedEIP712 = Field(
        title="EIP 712 Binding",
        description="The EIP-712 binding context is a set of constraints that must be verified by the message being"
        "signed.",
    )
