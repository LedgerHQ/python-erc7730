from pathlib import Path

import pytest

from erc7730.convert.ledger.eip712.convert_erc7730_v2_to_eip712 import ERC7730V2toEIP712Converter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_EIP712_DESCRIPTORS

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("input_file", ERC7730_EIP712_DESCRIPTORS, ids=path_id)
def test_erc7730_registry_files(input_file: Path) -> None:
    """
    Test converting ERC-7730 => Ledger legacy EIP-712.

    Note the test only applies to descriptors with a single contract and message, and only checks output files are
    compliant with the Ledger legacy EIP-712 json schema.
    """
    input_descriptor = InputERC7730Descriptor.load(input_file)
    result = ERC7730V2toEIP712Converter().convert(input_descriptor)
    assert result is not None, f"Conversion failed for {input_file.name}"
