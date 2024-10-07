from typing import Annotated

from pydantic import Field

from erc7730.model.path import ContainerPath, DataPath

ResolvedPath = Annotated[
    ContainerPath | DataPath,
    Field(
        title="Resolved Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed or the structured data schema (ABI path for contracts, path in the message types itself for EIP-712).",
        discriminator="type",
    ),
]
