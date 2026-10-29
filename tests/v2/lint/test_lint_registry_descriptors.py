import json
from pathlib import Path
from typing import Any

import pytest

from erc7730.common import client
from erc7730.common.abi import parse_signature
from erc7730.common.output import ListOutputAdder, Output
from erc7730.lint.v2.lint import lint_all
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.files import TEST_RESOURCES

RESOURCES = TEST_RESOURCES / "lint" / "v2"


def lint(path: Path, monkeypatch: pytest.MonkeyPatch) -> ListOutputAdder:
    """Lint a descriptor, with a reference ABI built from its format keys."""
    abis = [parse_signature(key) for key in InputERC7730Descriptor.load(path).display.formats]
    monkeypatch.setattr(client, "get_contract_abis", lambda chain_id, contract_address: abis)
    out = ListOutputAdder()
    lint_all([path], out)
    return out


def errors(out: ListOutputAdder) -> list[Output]:
    return [output for output in out.outputs if output.level == Output.Level.ERROR]


@pytest.mark.parametrize(
    "name",
    [
        # calldata with a constant chainId
        "calldata-base-OptimismPortal2.json",
        "calldata-blast-L2ToL1MessagePasser.json",
        # tokenAmount and tokenTicker with a relative chainIdPath
        "calldata-across-SpokePool-relative-chain-id-path.json",
        # addressName and tokenTicker on bytes32 arguments
        "calldata-bytes32-address.json",
    ],
)
def test_descriptor_lints_without_errors(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    assert errors(lint(RESOURCES / name, monkeypatch)) == []


def test_erc_example_maps_reports_only_the_invalid_token_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """The underlyingToken values of the ERC example are 21 bytes long, the shareToken map is valid."""
    out = lint(RESOURCES / "calldata-example-maps.json", monkeypatch)
    assert [output.title for output in errors(out)] == ["Invalid map value"]
    assert errors(out)[0].message.startswith('Value for key "1" in map $.metadata.maps.underlyingToken is invalid')


def write_descriptor(
    tmp_path: Path, fields: list[dict[str, Any]], maps: dict[str, Any] | None = None, chain_ids: tuple[int, ...] = (1,)
) -> Path:
    path = tmp_path / "calldata-test.json"
    path.write_text(
        json.dumps(
            {
                "$schema": "../../specs/erc7730-v2.schema.json",
                "context": {
                    "contract": {
                        "deployments": [
                            {"chainId": chain_id, "address": "0x0000000000000000000000000000000000000001"}
                            for chain_id in chain_ids
                        ]
                    }
                },
                "metadata": {
                    "owner": "Test Owner",
                    "maps": maps or {"tokens": {"values": {"1": "0x0000000000000000000000000000000000000002"}}},
                },
                "display": {
                    "formats": {
                        "execute(address target,uint256 amount,uint256 chainId,bytes data)": {
                            "intent": "Execute",
                            "fields": fields,
                        }
                    }
                },
            }
        )
    )
    return path


@pytest.mark.parametrize(
    "field",
    [
        {
            "path": "amount",
            "label": "Amount",
            "format": "tokenAmount",
            "params": {"token": {"map": "$.metadata.maps.tokens", "keyPath": "unknown"}},
        },
        {
            "path": "data",
            "label": "Call",
            "format": "calldata",
            "params": {"calleePath": "target", "chainIdPath": "unknown"},
        },
    ],
    ids=["map key path", "calldata chainIdPath"],
)
def test_parameter_path_not_in_abi_is_an_error(
    field: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = lint(write_descriptor(tmp_path, [field]), monkeypatch)
    assert [output.message for output in errors(out) if "`#.unknown`" in output.message] != []


def map_field(format: str, param: str, key_path: str = "@.chainId") -> dict[str, Any]:
    params: dict[str, Any] = {param: {"map": "$.metadata.maps.values", "keyPath": key_path}}
    path = {"tokenAmount": "amount", "calldata": "data", "addressName": "target"}[format]
    if format == "calldata" and param != "callee":
        params["calleePath"] = "target"
    if format == "tokenAmount" and param != "token":
        params["tokenPath"] = "target"
    return {"path": path, "label": "Field", "format": format, "params": params}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (map_field("tokenAmount", "token"), "hello"),
        (map_field("tokenAmount", "token"), "0x0000000000000000000000000000000000deadbeef"),
        (map_field("tokenAmount", "token"), None),
        (map_field("tokenAmount", "chainId"), "abc"),
        (map_field("calldata", "callee"), 1),
        (map_field("calldata", "amount"), -1),
        (map_field("calldata", "chainId"), True),
        (map_field("addressName", "senderAddress"), ["0x0000000000000000000000000000000000000002", "abc"]),
    ],
    ids=[
        "token not an address",
        "token of 21 bytes",
        "token null",
        "chainId not an integer",
        "callee not an address",
        "amount negative",
        "chainId boolean",
        "senderAddress list with an invalid address",
    ],
)
def test_invalid_map_value_is_an_error(
    field: dict[str, Any], value: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    maps = {"values": {"values": {"1": value}}}
    out = lint(write_descriptor(tmp_path, [field], maps), monkeypatch)
    assert [output.title for output in errors(out)] == ["Invalid map value"]


def test_map_keyed_by_chain_id_must_have_a_value_for_each_deployment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    maps = {"values": {"values": {"1": "0x0000000000000000000000000000000000000002"}}}
    path = write_descriptor(tmp_path, [map_field("tokenAmount", "token")], maps, chain_ids=(1, 10))
    out = lint(path, monkeypatch)
    assert [(output.title, "chain 10" in output.message) for output in errors(out)] == [("Missing map value", True)]


def test_map_keyed_by_transaction_data_needs_no_value_for_each_deployment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    maps = {"values": {"values": {"1": "0x0000000000000000000000000000000000000002"}}}
    path = write_descriptor(tmp_path, [map_field("tokenAmount", "token", "chainId")], maps, chain_ids=(1, 10))
    assert errors(lint(path, monkeypatch)) == []
