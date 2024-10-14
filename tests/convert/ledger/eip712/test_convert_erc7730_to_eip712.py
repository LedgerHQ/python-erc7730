from pathlib import Path

import pytest

from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.ledger.eip712.convert_erc7730_to_eip712 import ERC7730toEIP712Converter
from erc7730.convert.resolved.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_EIP712_DESCRIPTORS
from tests.schemas import assert_valid_legacy_eip_712
from tests.skip import single_or_skip


@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_erc7730_registry_files(input_file: Path) -> None:
    """
    Test converting ERC-7730 => Ledger legacy EIP-712.

    Note the test only applies to descriptors with a single contract and message, and only checks output files are
    compliant with the Ledger legacy EIP-712 json schema.
    """
    input_erc7730_descriptor = InputERC7730Descriptor.load(input_file)
    resolved_erc7730_descriptor = convert_and_print_errors(input_erc7730_descriptor, ERC7730InputToResolved())
    resolved_erc7730_descriptor = single_or_skip(resolved_erc7730_descriptor)
    output_descriptor = convert_and_print_errors(resolved_erc7730_descriptor, ERC7730toEIP712Converter())
    output_descriptor = single_or_skip(output_descriptor)
    assert_valid_legacy_eip_712(output_descriptor)
