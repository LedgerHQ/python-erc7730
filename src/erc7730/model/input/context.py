from pydantic import AnyUrl, Field

from erc7730.model.abi import ABI
from erc7730.model.base import Model
from erc7730.model.context import Deployment, Domain, EIP712JsonSchema, Factory
from erc7730.model.types import Id

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputContract(Model):
    """
    The contract binding context is a set constraints that are used to bind the ERC7730 file to a specific smart
    contract.
    """

    deployments: list[Deployment] = Field(
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments."
    )

    abi: list[ABI] | AnyUrl = Field(
        title="ABI",
        description="The ABI of the target contract. This can be either an array of ABI objects or an URL pointing to"
        "the ABI.",
    )

    addressMatcher: AnyUrl | None = Field(
        None,
        title="Address Matcher",
        description="An URL of a contract address matcher that should be used to match the contract address.",
    )

    factory: Factory | None = Field(
        None,
        title="Factory Constraint",
        description="A factory constraint is used to check whether the target contract is deployed by a specified"
        "factory.",
    )


class InputEIP712(Model):
    """
    TODO
    """

    deployments: list[Deployment] = Field(
        title="Deployments",
        description="An array of deployments describing where the contract is deployed. The target contract (Tx to or"
        "factory) MUST match one of those deployments.",
    )

    domain: Domain | None = Field(
        default=None,
        title="EIP 712 Domain Binding constraint",
        description="Each value of the domain constraint MUST match the corresponding eip 712 message domain value.",
    )

    domainSeparator: str | None = Field(
        default=None,
        title="Domain Separator constraint",
        description="The domain separator value that must be matched by the message. In hex string representation.",
    )

    schemas: list[EIP712JsonSchema | AnyUrl] = Field(title="TODO", description="TODO")


class InputContractContext(Model):
    """
    TODO
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    contract: InputContract = Field(title="TODO", description="TODO")


class InputEIP712Context(Model):
    """
    TODO
    """

    id: Id | None = Field(
        alias="$id",
        default=None,
        title="Id",
        description="An internal identifier that can be used either for clarity specifying what the element is or as a"
        "reference in device specific sections.",
    )

    eip712: InputEIP712 = Field(title="TODO", description="TODO")
