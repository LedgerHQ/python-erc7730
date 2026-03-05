"""
Package implementing an object model for ERC-7730 v2 resolved descriptors.

This model represents descriptors after resolution phase:
    - URLs have been fetched
    - Contract addresses have been normalized to lowercase
    - References have been inlined
    - Constants have been inlined
    - Field definitions have been inlined
    - Nested fields have been flattened where possible
    - Selectors have been converted to 4 bytes form
"""

from pydantic import Field

from erc7730.model.base import Model
from erc7730.model.resolved.v2.context import ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.v2.display import ResolvedDisplay
from erc7730.model.resolved.v2.metadata import ResolvedMetadata


class ResolvedERC7730Descriptor(Model):
    """
    An ERC-7730 v2 Clear Signing descriptor, after resolution phase.

    This model represents the descriptor after all references have been resolved and constants inlined.

    Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs

    JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v2.schema.json
    """

    schema_: str | None = Field(
        None,
        alias="$schema",
        description="The schema that the document should conform to. This should be the URL of a version of the clear "
        "signing JSON schemas available under "
        "https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs",
    )

    comment: str | None = Field(
        None,
        alias="$comment",
        description="An optional comment string that can be used to document the purpose of the file.",
    )

    context: ResolvedContractContext | ResolvedEIP712Context = Field(
        title="Binding Context Section",
        description="The binding context is a set of constraints that are used to bind the ERC7730 file to a specific"
        "structured data being displayed. Currently, supported contexts include contract-specific"
        "constraints or EIP712 message specific constraints.",
    )

    metadata: ResolvedMetadata = Field(
        title="Metadata Section",
        description="The metadata section contains information about constant values relevant in the scope of the"
        "current contract / message (as matched by the `context` section)",
    )

    display: ResolvedDisplay = Field(
        title="Display Formatting Info Section",
        description="The display section contains all the information needed to format the data in a human readable"
        "way. It contains the constants and formatters used to display the data contained in the bound structure.",
    )
