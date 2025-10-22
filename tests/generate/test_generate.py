from glob import glob
from pathlib import Path

import pytest
from rich import print

from erc7730.generate.generate import generate_descriptor
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.input.display import InputFieldDescription, InputNestedFields
from erc7730.model.input.lenses import get_deployments
from erc7730.model.paths import Array, DataPath, Field
from erc7730.model.types import Address

DATA = Path(__file__).resolve().parent / "data"


@pytest.mark.parametrize(
    "label,chain_id,contract_address",
    [
        ("Tether USD", 42161, Address("0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9")),
        ("POAP Bridge", 1, Address("0x0bb4d3e88243f4a057db77341e6916b0e449b158")),
        ("QuickSwap", 137, Address("0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff")),
        ("1inch Aggregation router v5", 10, Address("0x1111111254EEB25477B68fb85Ed929f73A960582")),
        ("Paraswap v5 AugustusSwapper", 10, Address("0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57")),
        ("Uniswap v3 Router 2", 8453, Address("0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD")),
    ],
)
def test_generate_from_contract_address(label: str, chain_id: int, contract_address: Address) -> None:
    """Generate descriptor using a provided ABI file."""
    _assert_descriptor_valid(generate_descriptor(chain_id=chain_id, contract_address=contract_address, owner=label))


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "abis*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_abis_buffer(test_file: str) -> None:
    """Generate descriptor using a provided ABI file."""
    with open(test_file, "rb") as f:
        _assert_descriptor_valid(
            generate_descriptor(
                chain_id=1, contract_address=Address("0x0000000000000000000000000000000000000000"), abi=f.read()
            )
        )


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "abis*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_abis_string(test_file: str) -> None:
    """Generate descriptor using a provided ABI file."""
    with open(test_file, "rb") as f:
        abi = f.read().decode("utf-8")
    _assert_descriptor_valid(
        generate_descriptor(chain_id=1, contract_address=Address("0x0000000000000000000000000000000000000000"), abi=abi)
    )


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "schemas*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_eip712_schemas_buffer(test_file: str) -> None:
    """Generate descriptor using a provided EIP-712 file."""
    with open(test_file, "rb") as f:
        _assert_descriptor_valid(
            generate_descriptor(
                chain_id=1,
                contract_address=Address("0x0000000000000000000000000000000000000000"),
                eip712_schema=f.read(),
            )
        )


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "schemas*.json"))), ids=lambda f: Path(f).stem)
def test_generate_from_eip712_schemas_string(test_file: str) -> None:
    """Generate descriptor using a provided EIP-712 file."""
    with open(test_file, "rb") as f:
        schema = f.read().decode("utf-8")
    _assert_descriptor_valid(
        generate_descriptor(
            chain_id=1,
            contract_address=Address("0x0000000000000000000000000000000000000000"),
            eip712_schema=schema,
        )
    )


def test_generate_array_of_structs() -> None:
    """Test that arrays of structs generate the expected nested fields"""
    test_file = DATA / "abis_array_struct.json"
    with open(test_file, "rb") as f:
        descriptor = generate_descriptor(
            chain_id=1, contract_address=Address("0x0000000000000000000000000000000000000000"), abi=f.read()
        )

    assert "processOrders((address,uint256,address)[])" in descriptor.display.formats
    format = descriptor.display.formats["processOrders((address,uint256,address)[])"]

    # First level is only 1 field, the array with path #.orders[]
    assert len(format.fields) == 1
    array_field = format.fields[0]
    assert isinstance(array_field, InputNestedFields)
    assert array_field.path == DataPath(absolute=True, elements=[Field(identifier="orders"), Array()])

    # Second level is 3 fields, the struct components with relative path token, amount and recipient
    assert len(array_field.fields) == 3
    field_names = ["token", "amount", "recipient"]
    for field, field_name in zip(array_field.fields, field_names, strict=False):
        assert isinstance(field, InputFieldDescription)
        assert isinstance(field.path, DataPath)
        assert field.path.absolute is False
        assert len(field.path.elements) == 1
        assert isinstance(field.path.elements[0], Field)
        assert field.path.elements[0].identifier == field_name


def test_generate_multidimensional_arrays() -> None:
    """Test that multidimensional arrays generate the expected field structure"""
    test_file = DATA / "abis_multidim_arrays.json"
    with open(test_file, "rb") as f:
        descriptor = generate_descriptor(
            chain_id=1, contract_address=Address("0x0000000000000000000000000000000000000000"), abi=f.read()
        )

    # Test 2D address array: address[][]
    assert "process2DAddresses(address[][])" in descriptor.display.formats
    format_2d = descriptor.display.formats["process2DAddresses(address[][])"]
    assert len(format_2d.fields) == 1
    field = format_2d.fields[0]
    assert isinstance(field, InputFieldDescription)
    assert field.path == DataPath(absolute=True, elements=[Field(identifier="addresses"), Array(), Array()])

    # Test 3D uint array: uint256[][][]
    # For basic types, all array dimensions are in the path, no nesting
    assert "process3DUints(uint256[][][])" in descriptor.display.formats
    format_3d = descriptor.display.formats["process3DUints(uint256[][][])"]

    assert len(format_3d.fields) == 1
    field = format_3d.fields[0]
    assert isinstance(field, InputFieldDescription)
    assert field.path == DataPath(absolute=True, elements=[Field(identifier="values"), Array(), Array(), Array()])

    # Test 2D tuple array: (address,uint256)[][]
    # For structs, there is a single NestedField with all array dimensions in path
    assert "process2DTuples((address,uint256)[][])" in descriptor.display.formats
    format_2d_tuple = descriptor.display.formats["process2DTuples((address,uint256)[][])"]

    # NestedFields with path #.orders[][]
    assert len(format_2d_tuple.fields) == 1
    nested = format_2d_tuple.fields[0]
    assert isinstance(nested, InputNestedFields)
    assert nested.path == DataPath(absolute=True, elements=[Field(identifier="orders"), Array(), Array()])

    # 2 FieldDescriptions for the tuple components
    assert len(nested.fields) == 2
    field_names = ["token", "amount"]
    for field, field_name in zip(nested.fields, field_names, strict=False):
        assert isinstance(field, InputFieldDescription)
        assert isinstance(field.path, DataPath)
        assert field.path.absolute is False
        assert len(field.path.elements) == 1
        assert isinstance(field.path.elements[0], Field)
        assert field.path.elements[0].identifier == field_name


def _assert_descriptor_valid(descriptor: InputERC7730Descriptor) -> None:
    print(descriptor.to_json_string())
    assert len(get_deployments(descriptor)) == 1
    assert len(descriptor.display.formats) > 0
    for format in descriptor.display.formats.values():
        assert len(format.fields) > 0
