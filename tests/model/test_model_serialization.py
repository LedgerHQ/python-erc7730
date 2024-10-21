import json
from pathlib import Path

import pytest

from erc7730.common.json import read_json_with_includes
from erc7730.model.input.descriptor import InputERC7730Descriptor
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

    assert_valid_erc_7730(InputERC7730Descriptor.load(input_file))


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_round_trip(input_file: Path) -> None:
    """Test model serializes back to same JSON."""
    actual = json.loads(InputERC7730Descriptor.load(input_file).to_json_string())
    expected = read_json_with_includes(input_file)
    assert_dict_equals(expected, actual)
