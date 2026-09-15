"""
Object model for ERC-7730 v2 descriptors `context` section.

"""

from typing import Any, Self

from pydantic import Field, model_validator
from pydantic_string_url import HttpUrl

from erc7730.model.base import Model
from erc7730.model.types import Id, MixedCaseAddress

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputDomain(Model):
    """
    EIP 712 Domain Binding constraint.

    Each value of the domain constraint MUST match the corresponding eip 712 message domain value.
    """

    name: str | None = Field(default=None, title="Name", description="The EIP-712 domain name.")

    version: str | None = Field(default=None, title="Version", description="The EIP-712 version.")

    chainId: int | None = Field(default=None, title="Chain ID", description="The EIP-155 chain id.")

    verifyingContract: MixedCaseAddress | None = Field(
        default=None, title="Verifying Contract", description="The EIP-712 verifying contract address."
    )

    salt: str | None = Field(default=None, title="Salt", description="The EIP-712 domain salt (bytes32 hex string).")


class InputDeployment(Model):
    """
    A deployment describing where the contract is deployed.

    The target contract (Tx to or factory) MUST match one of those deployments.
    """

    chainId: int = Field(title="Chain ID", description="The deployment EIP-155 chain id.")

    address: MixedCaseAddress = Field(title="Contract Address", description="The deployment contract address.")


class InputFactory(Model):
    """
    A factory constraint is used to check whether the target contract is deployed by a specified factory.
    """

    deployments: list[InputDeployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
    )

    deployEvent: str = Field(
        title="Deploy Event signature",
        description="The event signature that the factory emits when deploying a new contract.",
    )


class InputBindingContext(Model):
    deployments: list[InputDeployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
        min_length=1,
    )


class InputContract(InputBindingContext):
    """
    The contract binding context is a set constraints that are used to bind the ERC7730 file to a specific smart
    contract.
    """

    abi: Any | None = Field(
        None,
        title="ABI",
        description=(
            "[Deprecated] ABI definition bound to this file."
            "Continue providing it for backward compatibility only; new specs should rely on display formats."
        ),
    )

    addressMatcher: HttpUrl | None = Field(
        None,
        title="Address Matcher",
        description="An URL of a contract address matcher that should be used to match the contract address.",
    )

    factory: InputFactory | None = Field(
        None,
        title="Factory Constraint",
        description="A factory constraint is used to check whether the target contract is deployed by a specified"
        "factory.",
    )


class InputEIP712(InputBindingContext):
    """
    EIP 712 Binding.

    The EIP-712 binding context is a set of constraints that must be verified by the message being signed.
    """

    domain: InputDomain | None = Field(
        default=None,
        title="EIP 712 Domain Binding constraint",
        description="Each value of the domain constraint MUST match the corresponding eip 712 message domain value.",
    )

    domainSeparator: str | None = Field(
        default=None,
        title="Domain Separator constraint",
        description="The domain separator value that must be matched by the message. In hex string representation.",
    )

    deployments: list[InputDeployment] = Field(
        default_factory=list,
        title="Deployments",
        description="An array of deployments describing where the message is used. May be omitted when the descriptor "
        "binds through domainSeparator, which is the only option available to a domain that carries the chain id in "
        "salt and so has no chainId member.",
    )

    schemas: Any | None = Field(
        None,
        title="EIP-712 messages schemas",
        description=(
            "[Deprecated] Schema definition bound to this file. "
            "This is deprecated in favor of format driven validation. "
            "The address book should be used to resolve EIP-712 schemas."
        ),
    )

    @model_validator(mode="after")
    def _validate_binding(self) -> Self:
        # an empty domainSeparator is no more a binding than a missing one
        if not self.deployments and not self.domainSeparator:
            raise ValueError("EIP-712 context must set at least one of deployments or domainSeparator.")
        return self


class InputContractContext(Model):
    """
    Contract Binding Context.

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

    contract: InputContract = Field(
        title="Contract Binding Context",
        description="The contract binding context is a set constraints that are used to bind the ERC7730 file to a"
        "specific smart contract.",
    )


class InputEIP712Context(Model):
    """
    EIP 712 Binding.

    The EIP-712 binding context is a set of constraints that must be verified by the message being signed.
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    eip712: InputEIP712 = Field(
        title="EIP 712 Binding",
        description="The EIP-712 binding context is a set of constraints that must be verified by the message being"
        "signed.",
    )
