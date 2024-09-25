import json
from jsonschema import validate, exceptions
from pathlib import Path

from erc7730.common.pydantic import json_file_from_model
from erc7730.model.erc7730_descriptor import ERC7730Descriptor
from erc7730.mapper.mapper import to_eip712_mapper, to_erc7730_mapper
from eip712 import EIP712DAppDescriptor
import pytest
import glob


inputs = glob.glob("clear-signing-erc7730-registry/registry/*/eip712*.json")

with open("tests/resources/eip712.schema.json", "r") as file:
    eip712_schema = json.load(file)


@pytest.mark.parametrize("input", inputs)
def test_roundtrip(input: str) -> None:
    erc7730Descriptor = ERC7730Descriptor.load_or_none(Path(input))
    assert erc7730Descriptor is not None
    assert isinstance(erc7730Descriptor, ERC7730Descriptor)
    eip712DappDescriptor = to_eip712_mapper(erc7730Descriptor)
    assert eip712DappDescriptor is not None
    assert isinstance(eip712DappDescriptor, EIP712DAppDescriptor)
    eip712_json_str_from_model = json_file_from_model(EIP712DAppDescriptor, eip712DappDescriptor)
    eip712_json_from_model = json.loads(eip712_json_str_from_model)
    try:
        validate(instance=eip712_json_from_model, schema=eip712_schema)
    except exceptions.ValidationError as ex:
        pytest.fail(
            f"After converting to eip712 descriptor, serialized data for {input} is not valid against schema: {ex}"
        )
    newErc7730Descriptor = to_erc7730_mapper(eip712DappDescriptor)
    assert newErc7730Descriptor is not None
    if erc7730Descriptor.context is not None and erc7730Descriptor.context.eip712.domain is not None:  # type: ignore
        assert newErc7730Descriptor.context.eip712.domain.name == erc7730Descriptor.context.eip712.domain.name  # type: ignore
