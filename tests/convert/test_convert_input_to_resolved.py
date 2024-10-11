from pathlib import Path

import pytest
from syrupy import SnapshotAssertion

from erc7730.convert.convert import convert_and_print_errors, convert_and_raise_errors
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS, TEST_RESOURCES
from tests.skip import single_or_skip


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_convert_registry_files(input_file: Path, snapshot: SnapshotAssertion) -> None:
    input_descriptor = InputERC7730Descriptor.load(input_file)
    output_descriptor = convert_and_raise_errors(input_descriptor, ERC7730InputToResolved())
    output_descriptor = single_or_skip(output_descriptor)
    assert output_descriptor.to_json_string() == snapshot


def test_convert_with_refs() -> None:
    input_descriptor = InputERC7730Descriptor.load(TEST_RESOURCES / "paraswap.json")
    output_descriptor = convert_and_print_errors(input_descriptor, ERC7730InputToResolved())
    single_or_skip(output_descriptor)
