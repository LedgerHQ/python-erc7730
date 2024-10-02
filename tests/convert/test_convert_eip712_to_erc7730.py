from pathlib import Path

import pytest
from eip712 import EIP712DAppDescriptor

from erc7730.common.pydantic import model_from_json_file_with_includes
from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.convert_eip712_to_erc7730 import EIP712toERC7730Converter
from tests.cases import path_id
from tests.files import LEGACY_EIP712_DESCRIPTORS
from tests.schemas import assert_valid_erc_7730


@pytest.mark.parametrize("input_file", LEGACY_EIP712_DESCRIPTORS, ids=path_id)
def test_convert_legacy_registry_files(input_file: Path) -> None:
    input_descriptor = model_from_json_file_with_includes(input_file, EIP712DAppDescriptor)
    output_descriptor = convert_and_print_errors(input_descriptor, EIP712toERC7730Converter())
    assert output_descriptor is not None
    if isinstance(output_descriptor, dict):
        pytest.skip("Multiple descriptors tests not supported")
    assert_valid_erc_7730(output_descriptor)
