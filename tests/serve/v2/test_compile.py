import json
from typing import Any

import pytest

from erc7730.common import client
from erc7730.serve.v2.compile import compile_json
from erc7730.serve.v2.model import Compiled, ConversionFailed, InvalidDescriptor
from tests.files import TEST_RESOURCES
from tests.io import load_json_file

RESOURCES = TEST_RESOURCES / "serve"


def _descriptor(**changes: Any) -> dict[str, Any]:
    return load_json_file(RESOURCES / "usdt-descriptor.json") | changes


def _with_label(label: str) -> dict[str, Any]:
    descriptor = _descriptor()
    next(iter(descriptor["display"]["formats"].values()))["fields"][0]["label"] = label
    return descriptor


@pytest.mark.parametrize("token", ["usdc", "usdt"])
def test_compile_json_matches_reference_output(token: str) -> None:
    result = compile_json((RESOURCES / f"{token}-descriptor.json").read_bytes())

    assert isinstance(result, Compiled)
    assert sorted(result.descriptors, key=lambda d: d["selector"]) == load_json_file(RESOURCES / f"{token}.json")
    assert result.diagnostics == ()


@pytest.mark.parametrize(
    "body, message",
    [
        (b"{not json", "Invalid JSON"),
        (json.dumps(_descriptor(display="not an object")).encode(), "display:"),
        (b"\xff", "Invalid JSON"),
        (json.dumps(_descriptor(metadata={"owner": "Café"})).encode(), "only accept ASCII text, found 'é'"),
        (json.dumps(_with_label("Café"), ensure_ascii=False).encode(), "only accept ASCII text, found 'é'"),
    ],
    ids=["not json", "not a descriptor", "not utf-8", "escaped non-ascii owner", "raw non-ascii label"],
)
def test_compile_json_rejects_invalid_descriptors(body: bytes, message: str) -> None:
    result = compile_json(body)

    assert isinstance(result, InvalidDescriptor)
    assert message in result.message


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"includes": "common.json"}, "includes: not supported, send the merged descriptor"),
        (
            {"metadata": {"owner": "Test Owner", "enums": {"mode": "https://example.com/enum.json"}}},
            "metadata.enums: remote enums are not supported: mode",
        ),
    ],
    ids=["includes", "remote enum"],
)
def test_compile_json_refuses_external_resources(
    changes: dict[str, Any], message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("no request expected")

    monkeypatch.setattr(client, "get", no_network)

    assert compile_json(json.dumps(_descriptor(**changes)).encode()) == InvalidDescriptor(message)


def test_compile_json_returns_conversion_errors() -> None:
    # a map key that cannot be encoded as a uint32 makes the selector fail to convert
    descriptor = _descriptor(
        metadata={
            "owner": "Test Owner",
            "maps": {"tokens": {"values": {"4294967296": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}}},
        },
        display={
            "formats": {
                "deposit(uint256 assets, uint32 marketId)": {
                    "intent": "Deposit",
                    "fields": [
                        {
                            "path": "assets",
                            "label": "Amount",
                            "format": "tokenAmount",
                            "params": {"token": {"map": "$.metadata.maps.tokens", "keyPath": "#.marketId"}},
                        }
                    ],
                }
            }
        },
    )

    result = compile_json(json.dumps(descriptor).encode())

    assert isinstance(result, ConversionFailed)
    assert [(d.level, d.title) for d in result.diagnostics] == [("error", "Invalid map key")]
