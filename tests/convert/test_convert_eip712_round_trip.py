from pathlib import Path

import pytest
from eip712 import EIP712DAppDescriptor

from erc7730.common.pydantic import model_from_json_file_with_includes
from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.convert_eip712_to_erc7730 import EIP712toERC7730Converter
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.convert.convert_erc7730_to_eip712 import ERC7730toEIP712Converter
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.assertions import assert_model_json_equals
from tests.cases import path_id
from tests.files import ERC7730_EIP712_DESCRIPTORS, LEGACY_EIP712_DESCRIPTORS


@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_roundtrip_from_erc7730(input_file: Path) -> None:
    input_erc7730_descriptor = InputERC7730Descriptor.load(input_file)
    resolved_erc7730_descriptor = convert_and_print_errors(input_erc7730_descriptor, ERC7730InputToResolved())
    assert resolved_erc7730_descriptor is not None
    legacy_eip712_descriptor = convert_and_print_errors(resolved_erc7730_descriptor, ERC7730toEIP712Converter())
    assert legacy_eip712_descriptor is not None
    output_erc7730_descriptor = convert_and_print_errors(legacy_eip712_descriptor, EIP712toERC7730Converter())
    assert output_erc7730_descriptor is not None
    assert_model_json_equals(input_erc7730_descriptor, output_erc7730_descriptor)


@pytest.mark.parametrize("input_file", LEGACY_EIP712_DESCRIPTORS, ids=path_id)
def test_roundtrip_from_legacy_eip712(input_file: Path) -> None:
    input_legacy_eip712_descriptor = model_from_json_file_with_includes(input_file, EIP712DAppDescriptor)
    input_erc7730_descriptor = convert_and_print_errors(input_legacy_eip712_descriptor, EIP712toERC7730Converter())
    assert input_erc7730_descriptor is not None
    resolved_erc7730_descriptor = convert_and_print_errors(input_erc7730_descriptor, ERC7730InputToResolved())
    assert resolved_erc7730_descriptor is not None
    output_legacy_eip712_descriptor = convert_and_print_errors(resolved_erc7730_descriptor, ERC7730toEIP712Converter())
    assert output_legacy_eip712_descriptor is not None
    assert_model_json_equals(input_legacy_eip712_descriptor, output_legacy_eip712_descriptor)
