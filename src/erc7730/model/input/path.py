from typing import Annotated

from pydantic import Field as PydanticField
from pydantic import GetPydanticSchema
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

INPUT_PATH_JSON_SCHEMA = chain_schema([str_schema(), no_info_plain_validator_function(parse_path)])
INPUT_PATH_CORE_SCHEMA = json_or_python_schema(
    json_schema=INPUT_PATH_JSON_SCHEMA,
    python_schema=core_schema.union_schema(
        [
            is_instance_schema(DataPath),
            is_instance_schema(ContainerPath),
            is_instance_schema(DescriptorPath),
            INPUT_PATH_JSON_SCHEMA,
        ]
    ),
    serialization=to_string_ser_schema(),
)

InputPath = Annotated[
    ContainerPath | DataPath | DescriptorPath,
    GetPydanticSchema(lambda _type, _handler: INPUT_PATH_CORE_SCHEMA),
    PydanticField(
        title="Input Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed, the structured data schema (ABI path for contracts, path in the message types itself for EIP-712), or"
        "the current file describing the structured data formatting.",
    ),
]

InputPathAsJson = Annotated[
    ContainerPath | DataPath | DescriptorPath,
    PydanticField(
        title="Input Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed, the structured data schema (ABI path for contracts, path in the message types itself for EIP-712), or"
        "the current file describing the structured data formatting.",
        discriminator="type",
    ),
]


INPUT_REFERENCE_JSON_SCHEMA = chain_schema([str_schema(), no_info_plain_validator_function(parse_path)])
INPUT_REFERENCE_CORE_SCHEMA = json_or_python_schema(
    json_schema=INPUT_REFERENCE_JSON_SCHEMA,
    python_schema=core_schema.union_schema([is_instance_schema(DescriptorPath), INPUT_REFERENCE_JSON_SCHEMA]),
    serialization=to_string_ser_schema(),
)


InputReferencePath = Annotated[
    DescriptorPath,
    GetPydanticSchema(lambda _type, _handler: INPUT_REFERENCE_CORE_SCHEMA),
    PydanticField(
        title="Reference Path",
        description="A path in the input designating value(s) either in the container of the structured data to be"
        "signed, the structured data schema (ABI path for contracts, path in the message types itself for EIP-712), or"
        "the current file describing the structured data formatting.",
    ),
]
