from pathlib import Path
from erc7730.common.json import read_json_with_includes
from erc7730.common.pydantic import json_file_from_model
from erc7730.model.context import AbiJsonSchemaItem
from erc7730.model.erc7730_descriptor import ERC7730Descriptor
from erc7730.model.display import Display
import pytest
import glob
import json
from jsonschema import validate, exceptions
from prettydiff import print_diff
from pydantic_core import ValidationError

files = glob.glob("clear-signing-erc7730-registry/registry/*/*[!stETH].json")

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
    print_diff(json_from_model, original_dict_with_includes)
    assert json_from_model == original_dict_with_includes


def test_23_unset_attributes_must_not_be_serialized_as_set() -> None:
    abi_item_json_str = '{"name":"approve","inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"outputs":[{"name":"","type":"bool"}],"type":"function"}'
    abi_item_json = json.loads(abi_item_json_str)
    abi_item = AbiJsonSchemaItem.model_validate(abi_item_json, strict=False)
    abi_item_json_str_deserialized = json_file_from_model(AbiJsonSchemaItem, abi_item)
    print_diff(abi_item_json_str, abi_item_json_str_deserialized)
    assert abi_item_json_str == abi_item_json_str_deserialized


def test_27_erc7730_allows_invalid_paths() -> None:
    errors = None
    try:
        ERC7730Descriptor.load_or_none(Path("tests/resources/eip712_wrong_path.json"))
    except ValidationError as ex:
        assert ex.error_count() == 4
        errors = ex.errors
    finally:
        assert errors is not None


def test_22_screens_serialization_not_symmetric() -> None:
    display_json_str = '{"formats":{"Permit":{"screens":{"stax":[{"type":"propertyPage","label":"DAI Permit","content":["spender","value","deadline"]}]}}}}'
    display_json = json.loads(display_json_str)
    display = Display.model_validate(display_json, strict=True)
    display_json_deserialized = json_file_from_model(Display, display)
    print_diff(display_json_str, display_json_deserialized)
    assert display_json_str == display_json_deserialized
