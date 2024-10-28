from eip712.model.schema import EIP712SchemaField, EIP712Type
from pydantic import Field
from pydantic_string_url import HttpUrl

from erc7730.model.base import Model

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class EIP712JsonSchema(Model):
    """
    EIP-712 message schema.
    """

    primaryType: EIP712Type = Field(title="Primary Type", description="The identifier of the schema primary type.")

    types: dict[EIP712Type, list[EIP712SchemaField]] = Field(
        title="Types", description="The schema types reachable from primary type."
    )


class EIP712Schema(Model):
    """
    EIP-712 message schema.
    """

    eip712Schema: HttpUrl | EIP712JsonSchema = Field(
        title="EIP-712 message schema", description="The EIP-712 message schema."
    )
