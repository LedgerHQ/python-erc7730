"""
Package implementing an object model for ERC-7730 v2 input descriptors.

This model represents descriptors before resolution phase:
    - URLs have been not been fetched yet
    - Contract addresses have not been normalized to lowercase
    - References have not been inlined
    - Constants have not been inlined
    - Field definitions have not been inlined
    - Nested fields have been flattened where possible
    - Selectors have been converted to 4 bytes form
"""

from pydantic import Field

from erc7730.model.base import Model
from erc7730.model.input.v2.context import InputContractContext, InputEIP712Context
from erc7730.model.input.v2.display import InputDisplay
from erc7730.model.input.v2.metadata import InputMetadata


class InputERC7730Descriptor(Model):
    """
    An ERC-7730 v2 Clear Signing descriptor.

    This model is directly serializable back to the original JSON document.

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

    includes: str | None = Field(
        None,
        description="An URL of another ERC 7730 file that should be merged into this one. Includes are merged into "
        "this file before analysis. This can be used to manage interfaces definitions without redundancy.",
    )

    context: InputContractContext | InputEIP712Context = Field(
        title="Binding Context Section",
        description="The binding context is a set of constraints that are used to bind the ERC7730 file to a specific"
        "structured data being displayed. Currently, supported contexts include contract-specific"
        "constraints or EIP712 message specific constraints.",
    )

    metadata: InputMetadata = Field(
        title="Metadata Section",
        description="The metadata section contains information about constant values relevant in the scope of the"
        "current contract / message (as matched by the `context` section)",
    )

    display: InputDisplay = Field(
        title="Display Formatting Info Section",
        description="The display section contains all the information needed to format the data in a human readable"
        "way. It contains the constants and formatters used to display the data contained in the bound structure.",
    )
