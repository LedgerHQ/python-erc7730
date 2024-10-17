from erc7730.model.abi import Component, Function, InputOutput
from erc7730.model.paths.path_resolver import compute_abi_paths


def test_compute_paths_no_params() -> None:
    abi = Function(name="transfer", inputs=[])
    expected: set[str] = set()
    assert compute_abi_paths(abi) == expected


def test_compute_paths_with_params() -> None:
    abi = Function(
        name="transfer", inputs=[InputOutput(name="to", type="address"), InputOutput(name="amount", type="uint256")]
    )
    expected = {"to", "amount"}
    assert compute_abi_paths(abi) == expected


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
    assert compute_abi_paths(abi) == expected


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
                    Component(name="nested", type="tuple[]", components=[Component(name="deep", type="string")]),
                ],
            )
        ],
    )
    expected = {"bar.baz", "bar.qux", "bar.nested.[].deep"}
    assert compute_abi_paths(abi) == expected
