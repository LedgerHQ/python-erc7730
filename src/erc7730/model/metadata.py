"""
Object model for ERC-7730 descriptors `metadata` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

from datetime import datetime

from erc7730.model.base import Model

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class OwnerInfo(Model):
    legalName: str
    lastUpdate: datetime | None
    url: str


class TokenInfo(Model):
    name: str
    ticker: str
    decimals: int


class Metadata(Model):
    owner: str | None = None
    info: OwnerInfo | None = None
    token: TokenInfo | None = None
    constants: dict[str, str] | None = None
    enums: dict[str, str | dict[str, str]] | None = None
