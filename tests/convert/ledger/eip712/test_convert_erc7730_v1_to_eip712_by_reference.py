from pathlib import Path

import pytest
from eip712.model.input.descriptor import InputEIP712DAppDescriptor

from erc7730.common.json import dict_from_json_file
from erc7730.common.pydantic import model_to_json_dict
from erc7730.convert.convert import convert_and_print_errors
from erc7730.convert.ledger.eip712.convert_erc7730_to_eip712 import ERC7730toEIP712Converter
from erc7730.convert.resolved.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.assertions import assert_dict_equals
from tests.skip import single_or_skip

pytestmark = pytest.mark.v1

DATA = Path(__file__).resolve().parent / "data"


def test_uniswap_dutch_order() -> None:
    """Test converting ERC-7730 v1 => Ledger legacy EIP-712, comparing against reference output."""
    input_descriptor = InputERC7730Descriptor.load(DATA / "erc7730-UniswapX-DutchOrder-v1-input.json")
    resolved_descriptor = convert_and_print_errors(input_descriptor, ERC7730InputToResolved())
    resolved_descriptor = single_or_skip(resolved_descriptor)
    result = convert_and_print_errors(resolved_descriptor, ERC7730toEIP712Converter())
    output: InputEIP712DAppDescriptor = single_or_skip(result)
    assert_dict_equals(
        dict_from_json_file(DATA / "eip712-UniswapX-DutchOrder.json"),
        model_to_json_dict(output),
    )
