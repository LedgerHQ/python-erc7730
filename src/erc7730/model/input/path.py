from typing import Annotated

from pydantic import Field, GetPydanticSchema
from pydantic_core import core_schema
from pydantic_core.core_schema import (
    chain_schema,
    is_instance_schema,
    json_or_python_schema,
    no_info_plain_validator_function,
    str_schema,
    to_string_ser_schema,
)

from erc7730.model.path import ContainerPath, DataPath, DescriptorPath, parse_path

JSON_SCHEMA = chain_schema([str_schema(), no_info_plain_validator_function(parse_path)])
CORE_SCHEMA = json_or_python_schema(
    json_schema=JSON_SCHEMA,
    python_schema=core_schema.union_schema(
        [
            is_instance_schema(DataPath),
            is_instance_schema(ContainerPath),
            is_instance_schema(DescriptorPath),
            JSON_SCHEMA,
        ]
    ),
    serialization=to_string_ser_schema(),
)

InputPath = Annotated[
    ContainerPath | DataPath | DescriptorPath,
    GetPydanticSchema(lambda _type, _handler: CORE_SCHEMA),
    Field(
        title="Input Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed, the structured data schema (ABI path for contracts, path in the message types itself for EIP-712), or"
        "the current file describing the structured data formatting.",
    ),
]

InputPathAsJson = Annotated[
    ContainerPath | DataPath | DescriptorPath,
    Field(
        title="Input Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed, the structured data schema (ABI path for contracts, path in the message types itself for EIP-712), or"
        "the current file describing the structured data formatting.",
        discriminator="type",
    ),
]
