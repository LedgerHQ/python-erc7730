from erc7730.common.abi import compute_paths, compute_signature, reduce_signature, signature_to_selector
from erc7730.model.abi import Component, Function, InputOutput

# Thank you Github Copilot for generating the tests below!


def test_reduce_signature_no_params() -> None:
    signature = "transfer()"
    expected = "transfer()"
    assert reduce_signature(signature) == expected


def test_reduce_signature_without_names() -> None:
    signature = "transfer(address)"
    expected = "transfer(address)"
    assert reduce_signature(signature) == expected


def test_reduce_signature_with_names_and_spaces() -> None:
    signature = "mintToken(uint256 eventId, uint256 tokenId, address receiver, uint256 expirationTime, bytes signature)"
    expected = "mintToken(uint256,uint256,address,uint256,bytes)"
    assert reduce_signature(signature) == expected


def test_reduce_signature_invalid() -> None:
    signature = "invalid_signature"
    assert reduce_signature(signature) is None


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


def test_compute_paths_no_params() -> None:
    abi = Function(name="transfer", inputs=[])
    expected: set[str] = set()
    assert compute_paths(abi) == expected


def test_compute_paths_with_params() -> None:
    abi = Function(
        name="transfer", inputs=[InputOutput(name="to", type="address"), InputOutput(name="amount", type="uint256")]
    )
    expected = {"to", "amount"}
    assert compute_paths(abi) == expected


def test_compute_paths_with_nested_params() -> None:
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
    expected = {"bar.baz", "bar.qux"}
    assert compute_paths(abi) == expected


def test_compute_paths_with_multiple_nested_params() -> None:
    abi = Function(
        name="foo",
        inputs=[
            InputOutput(
                name="bar",
                type="tuple",
                components=[
                    Component(name="baz", type="uint256"),
                    Component(name="qux", type="address"),
                    Component(name="nested", type="tuple", components=[Component(name="deep", type="string")]),
                ],
            )
        ],
    )
    expected = {"bar.baz", "bar.qux", "bar.nested.deep"}
    assert compute_paths(abi) == expected
