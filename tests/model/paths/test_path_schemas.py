from eip712.model.schema import EIP712SchemaField

from erc7730.model.abi import Component, Function, InputOutput
from erc7730.model.context import EIP712JsonSchema
from erc7730.model.paths.path_parser import parse_path
from erc7730.model.paths.path_schemas import compute_abi_schema_paths, compute_eip712_schema_paths


def test_compute_abi_paths_no_params() -> None:
    abi = Function(name="transfer", inputs=[])
    expected: set[str] = set()
    assert compute_abi_schema_paths(abi) == expected


def test_compute_abi_paths_with_params() -> None:
    abi = Function(
        name="transfer", inputs=[InputOutput(name="to", type="address"), InputOutput(name="amount", type="uint256")]
    )
    expected = {parse_path("#.to"), parse_path("#.amount")}
    assert compute_abi_schema_paths(abi) == expected


def test_compute_abi_paths_with_nested_params() -> None:
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
    expected = {parse_path("#.bar.baz"), parse_path("#.bar.qux")}
    assert compute_abi_schema_paths(abi) == expected


def test_compute_abi_paths_with_multiple_nested_params() -> None:
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
    expected = {
        parse_path("#.bar.baz"),
        parse_path("#.bar.qux"),
        parse_path("#.bar.nested.[]"),
        parse_path("#.bar.nested.[].deep"),
    }
    assert compute_abi_schema_paths(abi) == expected


def test_compute_eip712_paths_with_multiple_nested_params() -> None:
    schema = EIP712JsonSchema(
        primaryType="Foo",
        types={
            "Foo": [
                EIP712SchemaField(name="bar", type="Bar"),
            ],
            "Bar": [
                EIP712SchemaField(name="baz", type="uint256"),
                EIP712SchemaField(name="qux", type="uint256"),
                EIP712SchemaField(name="nested", type="Nested[]"),
            ],
            "Nested": [
                EIP712SchemaField(name="deep", type="bytes"),
            ],
        },
    )
    expected = {
        parse_path("#.bar.baz"),
        parse_path("#.bar.qux"),
        parse_path("#.bar.nested.[]"),
        parse_path("#.bar.nested.[].deep"),
    }
    assert compute_eip712_schema_paths(schema) == expected
