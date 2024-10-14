from pathlib import Path

import pytest
from eip712 import EIP712DAppDescriptor

from erc7730.common.pydantic import model_from_json_file_with_includes
from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.ledger.eip712.convert_eip712_to_erc7730 import EIP712toERC7730Converter
from tests.cases import path_id
from tests.files import LEGACY_EIP712_DESCRIPTORS
from tests.schemas import assert_valid_erc_7730
from tests.skip import single_or_skip


@pytest.mark.parametrize("input_file", LEGACY_EIP712_DESCRIPTORS, ids=path_id)
def test_legacy_registry_files(input_file: Path) -> None:
    """
    Test converting Ledger legacy EIP-712 => ERC-7730.

    Note the test only applies to descriptors with a single contract and message, and only checks output files are
    compliant with the ERC-7730 json schema.
    """
    input_descriptor = model_from_json_file_with_includes(input_file, EIP712DAppDescriptor)
    output_descriptor = convert_and_print_errors(input_descriptor, EIP712toERC7730Converter())
    output_descriptor = single_or_skip(output_descriptor)
    assert_valid_erc_7730(output_descriptor)
