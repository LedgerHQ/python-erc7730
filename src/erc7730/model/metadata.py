"""
Object model for ERC-7730 descriptors `metadata` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

from datetime import datetime

from pydantic import Field

from erc7730.model.base import Model

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class OwnerInfo(Model):
    """
    TODO
    """

    legalName: str = Field(title="TODO", description="TODO")
    lastUpdate: datetime | None = Field(title="TODO", description="TODO")
    url: str = Field(title="TODO", description="TODO")


class TokenInfo(Model):
    """
    TODO
    """

    name: str = Field(title="TODO", description="TODO")

    ticker: str = Field(title="TODO", description="TODO")

    decimals: int = Field(title="TODO", description="TODO")


class Metadata(Model):
    """
    TODO
    """

    owner: str | None = Field(default=None, title="TODO", description="TODO")

    info: OwnerInfo | None = Field(default=None, title="TODO", description="TODO")

    token: TokenInfo | None = Field(default=None, title="TODO", description="TODO")

    constants: dict[str, str] | None = Field(default=None, title="TODO", description="TODO")

    enums: dict[str, str | dict[str, str]] | None = Field(default=None, title="TODO", description="TODO")
