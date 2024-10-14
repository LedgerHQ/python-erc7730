import json
from pathlib import Path

import pytest
from pydantic import RootModel

from erc7730.common.json import read_json_with_includes
from erc7730.common.pydantic import model_from_json_str, model_to_json_str
from erc7730.model.abi import ABI
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import InputDisplay
from tests.assertions import assert_dict_equals
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS
from tests.schemas import assert_valid_erc_7730


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_schema(input_file: Path) -> None:
    """Test model serializes to JSON that matches the schema."""

    # TODO: invalid files in registry
    if input_file.name in {"eip712-rarible-erc-1155.json", "eip712-rarible-erc-721.json"}:
        pytest.skip("Rarible EIP-712 schemas are missing EIP712Domain")
    if input_file.name in {"calldata-lpv2.json", "calldata-AugustusSwapper.json"}:
        pytest.skip("addressName `type` must be changed to `types`")

    assert_valid_erc_7730(InputERC7730Descriptor.load(input_file))


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_round_trip(input_file: Path) -> None:
    """Test model serializes back to same JSON."""

    # TODO: invalid files in registry
    if input_file.name in {"calldata-lpv2.json", "calldata-AugustusSwapper.json"}:
        pytest.skip("addressName `type` must be changed to `types`")

    actual = json.loads(InputERC7730Descriptor.load(input_file).to_json_string())
    expected = read_json_with_includes(input_file)
    assert_dict_equals(expected, actual)


def test_unset_attributes_must_not_be_serialized_as_set() -> None:
    """Test serialization does not include unset attributes."""
    input_json_str = (
        "{"
        '"name":"approve",'
        '"inputs":['
        '{"name":"_spender","type":"address"},'
        '{"name":"_value","type":"uint256"}'
        "],"
        '"outputs":['
        '{"name":"","type":"bool"}'
        "],"
        '"type":"function"}'
    )
    output_json_str = model_to_json_str(model_from_json_str(input_json_str, RootModel[ABI]).root)
    assert_dict_equals(json.loads(input_json_str), json.loads(output_json_str))


def test_22_screens_serialization_not_symmetric() -> None:
    """Test serialization of screens is symmetric."""
    input_json_str = (
        "{"
        '"formats":{'
        '"Permit":{'
        '"fields": [],'
        '"screens":{'
        '"stax":[{"type":"propertyPage","label":"DAI Permit","content":["spender","value","deadline"]}]'
        "}"
        "}"
        "}"
        "}"
    )
    output_json_str = model_to_json_str(model_from_json_str(input_json_str, InputDisplay))
    assert_dict_equals(json.loads(input_json_str), json.loads(output_json_str))
