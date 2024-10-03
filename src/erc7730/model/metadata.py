"""
Object model for ERC-7730 descriptors `metadata` section.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

from datetime import datetime

from pydantic import Field
from pydantic.v1 import AnyUrl

from erc7730.model.base import Model

# ruff: noqa: N815 - camel case field names are tolerated to match schema


class OwnerInfo(Model):
    """
    Main contract's owner detailed information.

    The owner info section contains detailed information about the owner or target of the contract / message to be
    clear signed.
    """

    legalName: str = Field(
        title="Owner Legal Name", description="The full legal name of the owner if different from the owner field."
    )

    lastUpdate: datetime | None = Field(
        title="Last Update of the contract / message",
        description="The date of the last update of the contract / message.",
    )

    url: AnyUrl = Field(title="Owner URL", description="URL with more info on the entity the user interacts with.")


class TokenInfo(Model):
    """
    Token Description.

    A description of an ERC20 token exported by this format, that should be trusted. Not mandatory if the
    corresponding metadata can be fetched from the contract itself.
    """

    name: str = Field(title="Token Name", description="The token display name.")

    ticker: str = Field(
        title="Token Ticker",
        description="A short capitalized ticker for the token, that will be displayed in front of corresponding"
        "amounts.",
    )

    decimals: int = Field(
        title="Token Decimals", description="The number of decimals of the token ticker, used to display amounts."
    )


class Metadata(Model):
    """
    Metadata Section.

    The metadata section contains information about constant values relevant in the scope of the current contract /
    message (as matched by the `context` section)
    """

    owner: str | None = Field(
        default=None,
        title="Owner display name.",
        description="The display name of the owner or target of the contract / message to be clear signed.",
    )

    info: OwnerInfo | None = Field(
        default=None,
        title="Main contract's owner detailed information.",
        description="The owner info section contains detailed information about the owner or target of the contract /"
        "message to be clear signed.",
    )

    token: TokenInfo | None = Field(
        default=None,
        title="Token Description",
        description="A description of an ERC20 token exported by this format, that should be trusted. Not mandatory if"
        "the corresponding metadata can be fetched from the contract itself.",
    )

    constants: dict[str, str] | None = Field(
        default=None,
        title="Constant values",
        description="A set of values that can be used in format parameters. Can be referenced with a path expression"
        "like $.metadata.constants.CONSTANT_NAME",
    )

    enums: dict[str, str | dict[str, str]] | None = Field(
        default=None,
        title="Enums",
        description="A set of enums that are used to format fields replacing values with human readable strings.",
    )


# TODO enums must be split into input/resolved, schema is:
# "enums" : {
#     "title": "Enums",
#     "type": "object",
#     "description": "A set of enums that are used to format fields replacing values with human readable strings.",
#
#     "additionalProperties": {
#         "oneOf": [
#             {
#                 "title": "A dynamic enum",
#                 "type": "string",
#                 "description": "A dynamic enum contains an URL which returns a json file with simple key-values
#                 mapping values display name. It is assumed those values can change between two calls to clear sign."
#             },
#             {
#                 "title": "Enumeration",
#                 "type": "object",
#                 "description": "A set of values that will be used to replace a field value with a human readable
#                 string. Enumeration keys are the field values and enumeration values are the displayable strings",
#
#                 "additionalProperties": {
#                     "type": "string"
#                 }
#             }
#         ]
#     }
# }
