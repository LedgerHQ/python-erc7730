from pathlib import Path

from erc7730.common.json import dict_from_json_file
from erc7730.common.pydantic import model_to_json_dict
from erc7730.convert.ledger.eip712.convert_erc7730_v2_to_eip712 import ERC7730V2toEIP712Converter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.assertions import assert_dict_equals

DATA = Path(__file__).resolve().parent / "data"


def test_uniswap_dutch_order() -> None:
    """Test converting ERC-7730 v2 => Ledger legacy EIP-712, comparing against reference output."""
    input_descriptor = InputERC7730Descriptor.load(DATA / "erc7730-UniswapX-DutchOrder-v2-input.json")
    result = ERC7730V2toEIP712Converter().convert(input_descriptor)
    assert result is not None
    assert "1" in result, "Expected chain ID 1 in output"
    assert_dict_equals(
        dict_from_json_file(DATA / "eip712-UniswapX-DutchOrder.json"),
        model_to_json_dict(result["1"]),
    )
