from glob import glob
from pathlib import Path

import pytest
from rich import print

from erc7730.generate.generate import generate_descriptor
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.lenses import get_deployments
from erc7730.model.types import Address

DATA = Path(__file__).resolve().parent / "data"


@pytest.mark.parametrize(
    "label,chain_id,contract_address",
    [
        ("Tether USD", 42161, Address("0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9")),
        ("POAP Bridge", 1, Address("0x0bb4d3e88243f4a057db77341e6916b0e449b158")),
        ("QuickSwap", 137, Address("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")),
        ("1inch Aggregation router v5", 10, Address("0x1111111254EEB25477B68fb85Ed929f73A960582")),
        ("Paraswap v5 AugustusSwapper", 137, Address("0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57")),
        ("Uniswap v3 Router 2", 8453, Address("0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD")),
    ],
)
def test_generate_from_contract_address(label: str, chain_id: int, contract_address: Address) -> None:
    """Generate descriptor using a provided ABI file."""
    _assert_descriptor_valid(generate_descriptor(chain_id=chain_id, contract_address=contract_address, owner=label))


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "abis*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_abis(test_file: str) -> None:
    """Generate descriptor using a provided ABI file."""
    _assert_descriptor_valid(
        generate_descriptor(
            chain_id=1, contract_address=Address("0x0000000000000000000000000000000000000000"), abi_file=Path(test_file)
        )
    )


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "schemas*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_eip712_schemas(test_file: str) -> None:
    """Generate descriptor using a provided EIP-712 file."""
    _assert_descriptor_valid(
        generate_descriptor(
            chain_id=1,
            contract_address=Address("0x0000000000000000000000000000000000000000"),
            eip712_schema_file=Path(test_file),
        )
    )


def _assert_descriptor_valid(descriptor: InputERC7730Descriptor) -> None:
    print(descriptor.to_json_string())
    assert len(get_deployments(descriptor)) == 1
    assert len(descriptor.display.formats) > 0
    for format in descriptor.display.formats.values():
        assert len(format.fields) > 0
