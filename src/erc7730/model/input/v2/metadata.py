"""
Object model for ERC-7730 v2 descriptors `metadata` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import Field
from pydantic_string_url import HttpUrl

from erc7730.model.base import Model
from erc7730.model.metadata import TokenInfo
from erc7730.model.resolved.metadata import EnumDefinition
from erc7730.model.types import Id, ScalarType

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class InputOwnerInfo(Model):
    """
    Main contract's owner detailed information (v2).

    The owner info section contains detailed information about the owner or target of the contract / message to be
    clear signed.

    Note: legalName and lastUpdate are v1 backward compatibility extensions not present in the v2 JSON schema.
    The v2 schema only defines deploymentDate and url for info. These fields are retained for smooth migration.
    """

    legalName: str | None = Field(
        None,
        title="Owner Legal Name",
        description="[v1 compat] The full legal name of the owner if different from the owner field. "
        "Not present in v2 schema, retained for backward compatibility.",
        min_length=1,
        examples=["Tether Limited", "Lido DAO"],
    )

    lastUpdate: datetime | None = Field(
        default=None,
        title="[DEPRECATED] Last Update of the contract / message",
        description="[v1 compat] The date of the last update of the contract / message. "
        "Not present in v2 schema, retained for backward compatibility. Use `deploymentDate` instead.",
        examples=[datetime.now(UTC)],
    )

    deploymentDate: datetime | None = Field(
        default=None,
        title="Deployment date of contract / message",
        description="The date of deployment of the contract / message.",
        examples=[datetime.now(UTC)],
    )

    url: HttpUrl = Field(
        title="Owner URL",
        description="URL with more info on the entity the user interacts with.",
        examples=[HttpUrl("https://tether.to"), HttpUrl("https://lido.fi")],
    )


class InputMapDefinition(Model):
    """
    A map definition for context-dependent constants.

    Maps are used to provide context-dependent values based on a key resolution.
    """

    keyType: str | None = Field(
        None,
        alias="$keyType",
        title="Key Type",
        description="The type of the key used for map resolution.",
    )

    values: dict[str, Any] = Field(
        title="Map Values",
        description="The mapping of keys to values that will be used for dynamic resolution.",
        min_length=1,
    )


class InputMetadata(Model):
    """
    Metadata Section (v2).

    The metadata section contains information about constant values relevant in the scope of the current contract /
    message (as matched by the `context` section)
    """

    owner: str | None = Field(
        default=None,
        title="Owner display name.",
        description="The display name of the owner or target of the contract / message to be clear signed.",
    )

    contractName: str | None = Field(
        default=None,
        title="Contract Name",
        description="The name of the contract targeted by the transaction or message.",
    )

    info: InputOwnerInfo | None = Field(
        default=None,
        title="Main contract's owner detailed information.",
        description="The owner info section contains detailed information about the owner or target of the contract / "
        "message to be clear signed.",
    )

    token: TokenInfo | None = Field(
        default=None,
        title="Token Description",
        description="A description of an ERC20 token exported by this format, that should be trusted. Not mandatory if "
        "the corresponding metadata can be fetched from the contract itself.",
    )

    constants: dict[Id, ScalarType | None] | None = Field(
        default=None,
        title="Constant values",
        description="A set of values that can be used in format parameters. Can be referenced with a path expression "
        "like $.metadata.constants.CONSTANT_NAME",
        examples=[
            {
                "token_path": "#.params.witness.outputs[0].token",
                "native_currency": "0x0000000000000000000000000000000000000001",
                "max_threshold": "0xFFFFFFFF",
                "max_message": "Max",
            }
        ],
    )

    enums: dict[Id, HttpUrl | EnumDefinition] | None = Field(
        default=None,
        title="Enums",
        description="A set of enums that are used to format fields replacing values with human readable strings.",
        examples=[{"interestRateMode": {"1": "stable", "2": "variable"}, "vaultIDs": "https://example.com/vaultIDs"}],
        max_length=32,  # TODO refine
    )

    maps: dict[Id, InputMapDefinition] | None = Field(
        default=None,
        title="Maps",
        description="A set of maps that are used to manage context dependent constants. Maps can be used in place of "
        "constants, and the corresponding constant is based on the map key resolved value.",
        examples=[
            {"tokenMap": {"$keyType": "address", "values": {"0xA0b86a33E6441...": "USDT", "0x6B175474E89...": "DAI"}}}
        ],
    )
