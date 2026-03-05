import json
import re
from pathlib import Path
from typing import Any

import pytest

from erc7730.common.json import read_json_with_includes
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.assertions import assert_dict_equals
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS
from tests.schemas import assert_valid_erc_7730

HEX_STRING_RE = re.compile(r"^0x[0-9a-fA-F]+$")


def remove_nulls(value: dict[Any, Any]) -> dict[Any, Any]:
    if isinstance(value, dict):
        return {k: remove_nulls(v) for k, v in value.items() if v is not None}
    elif isinstance(value, list):
        return [remove_nulls(item) for item in value if item is not None]
    else:
        return value


def normalize_hex_strings(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: normalize_hex_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_hex_strings(item) for item in value]
    if isinstance(value, str) and HEX_STRING_RE.match(value):
        return value.lower()
    return value


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
    actual = normalize_hex_strings(json.loads(InputERC7730Descriptor.load(input_file).to_json_string()))
    expected = normalize_hex_strings(remove_nulls(read_json_with_includes(input_file)))
    assert_dict_equals(expected, actual)
