"""
Base types for ERC-7730 descriptors.

Specification: https://github.com/LedgerHQ/clear-signing-erc7730-registry/tree/master/specs
JSON schema: https://github.com/LedgerHQ/clear-signing-erc7730-registry/blob/master/specs/erc7730-v1.schema.json
"""

from typing import Annotated

from pydantic import Field

Id = Annotated[str, Field(min_length=1)]
ContractAddress = Annotated[str, Field(min_length=0, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")]
Path = Annotated[str, Field(pattern=r"^[a-zA-Z0-9.\[\]_@\$\#]+")]
