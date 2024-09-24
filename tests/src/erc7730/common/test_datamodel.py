from pathlib import Path
from erc7730.common.json import read_json_with_includes
from erc7730.common.pydantic import json_file_from_model
from erc7730.model.erc7730_descriptor import ERC7730Descriptor
import pytest
import glob
import json
from jsonschema import validate, exceptions

files = glob.glob("clear-signing-erc7730-registry/registry/*/*.json")
with open("clear-signing-erc7730-registry/specs/erc7730-v1.schema.json", "r") as file:
    schema = json.load(file)


@pytest.mark.parametrize("file", files)
def test_from_erc7730(file: str) -> None:
    original_dict_with_includes = read_json_with_includes(Path(file))
    model_erc7730 = ERC7730Descriptor.load_or_none(Path(file))
    assert model_erc7730 is not None
    json_str_from_model = json_file_from_model(ERC7730Descriptor, model_erc7730)
    json_from_model = json.loads(json_str_from_model)
    try:
        validate(instance=json_from_model, schema=schema)
    except exceptions.ValidationError as ex:
        pytest.fail(f"Invalid schema for serialized data from {file}: {ex}")
    assert json_from_model == original_dict_with_includes
