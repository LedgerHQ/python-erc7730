from pathlib import Path

import pytest

from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.convert.convert_erc7730_to_eip712 import ERC7730toEIP712Converter
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_EIP712_DESCRIPTORS
from tests.schemas import assert_valid_legacy_eip_712


@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_erc7730_registry_files(input_file: Path) -> None:
    input_erc7730_descriptor = InputERC7730Descriptor.load(input_file)
    resolved_erc7730_descriptor = convert_and_print_errors(input_erc7730_descriptor, ERC7730InputToResolved())
    assert resolved_erc7730_descriptor is not None
    if isinstance(resolved_erc7730_descriptor, dict):
        pytest.skip("Multiple descriptors tests not supported")
    output_descriptor = convert_and_print_errors(resolved_erc7730_descriptor, ERC7730toEIP712Converter())
    assert output_descriptor is not None
    if isinstance(output_descriptor, dict):
        pytest.skip("Multiple descriptors tests not supported")
    assert_valid_legacy_eip_712(output_descriptor)
