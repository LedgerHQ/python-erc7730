import pytest

from erc7730.common.abi import (
    compute_signature,
    reduce_signature,
    signature_to_selector,
)
from erc7730.model.abi import Component, Function, InputOutput


@pytest.mark.parametrize(
    "signature, expected",
    [
        # no param, no space
        ("transfer()", "transfer()"),
        # one param, no space
        ("transfer(address)", "transfer(address)"),
        # multiple params, expected spaces, no names
        ("mintToken(uint256, uint256, address, uint256, bytes)", "mintToken(uint256,uint256,address,uint256,bytes)"),
        # multiple params, expected spaces, names
        (
            "mintToken(uint256 eventId, uint256 tokenId, address receiver, uint256 expirationTime, bytes signature)",
            "mintToken(uint256,uint256,address,uint256,bytes)",
        ),
        # multiple params, spaces everywhere, names, end with tuple
        (
            "f1( uint256[] _a , address _o , ( uint256 v , uint256 d ) _p )",
            "f1(uint256[],address,(uint256,uint256))",
        ),
        # multiple params, spaces everywhere, names, tuple in middle
        (
            "f2( uint256[] _a , ( uint256 v , uint256 d ) _p , address _o )",
            "f2(uint256[],(uint256,uint256),address)",
        ),
        # multiple params, spaces everywhere, names, nested tuples
        (
            "f3( uint256[] _a , ( uint256 v , ( bytes s , address a ) , uint256 d ) _p , address _o )",
            "f3(uint256[],(uint256,(bytes,address),uint256),address)",
        ),
    ],
)
def test_reduce_signature(signature: str, expected: str) -> None:
    # This test covers both parse_signature and compute_signature
    assert reduce_signature(signature) == expected


def test_compute_signature_no_params() -> None:
    abi = Function(name="transfer", inputs=[])
    expected = "transfer()"
    assert compute_signature(abi) == expected


def test_compute_signature_with_params() -> None:
    abi = Function(
        name="transfer", inputs=[InputOutput(name="to", type="address"), InputOutput(name="amount", type="uint256")]
    )
    expected = "transfer(address,uint256)"
    assert compute_signature(abi) == expected


def test_compute_signature_with_nested_params() -> None:
    abi = Function(
        name="foo",
        inputs=[
            InputOutput(
                name="bar",
                type="tuple",
                components=[Component(name="baz", type="uint256"), Component(name="qux", type="address")],
            )
        ],
    )
    expected = "foo((uint256,address))"
    assert compute_signature(abi) == expected


def test_signature_to_selector() -> None:
    signature = "transfer(address,uint256)"
    expected = "0xa9059cbb"
    assert signature_to_selector(signature) == expected
