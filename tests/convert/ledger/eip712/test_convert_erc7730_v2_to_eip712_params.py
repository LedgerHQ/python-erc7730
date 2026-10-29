import json
from typing import Any

from erc7730.common.output import ListOutputAdder, Output
from erc7730.convert.ledger.eip712.convert_erc7730_v2_to_eip712 import ERC7730V2toEIP712Converter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

ENCODE_TYPE = "Order(address token,uint256 amount,address target,uint256 chainId,bytes data)"


def convert(field: dict[str, Any]) -> tuple[dict[str, Any] | None, ListOutputAdder]:
    """Convert a minimal v2 EIP-712 descriptor around a single display field, and return its legacy field."""
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "eip712": {
                        "domain": {"name": "Test"},
                        "deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}],
                    }
                },
                "metadata": {
                    "owner": "Test Owner",
                    "maps": {"tokens": {"values": {"1": "0x0000000000000000000000000000000000000002"}}},
                },
                "display": {"formats": {ENCODE_TYPE: {"intent": "Order", "fields": [field]}}},
            }
        )
    )
    out = ListOutputAdder()
    if (result := ERC7730V2toEIP712Converter().convert(descriptor, out)) is None:
        return None, out
    fields = result["1"].contracts[0].messages[0].mapper.fields
    assert len(fields) == 1
    return fields[0].model_dump(exclude_none=True), out


def error_messages(out: ListOutputAdder) -> list[str]:
    return [output.message for output in out.outputs if output.level == Output.Level.ERROR]


def test_calldata_chain_id_path_is_converted() -> None:
    field, out = convert(
        {
            "path": "data",
            "label": "Call",
            "format": "calldata",
            "params": {"calleePath": "target", "chainIdPath": "chainId"},
        }
    )

    assert error_messages(out) == []
    assert field is not None
    assert field["calleePath"] == "target"
    assert field["chainIdPath"] == "chainId"


def test_calldata_constant_chain_id_is_rejected() -> None:
    field, out = convert(
        {"path": "data", "label": "Call", "format": "calldata", "params": {"calleePath": "target", "chainId": 10}}
    )

    assert field is None
    assert any('"chainId"' in message for message in error_messages(out))


def test_token_map_reference_is_rejected() -> None:
    field, out = convert(
        {
            "path": "amount",
            "label": "Amount",
            "format": "tokenAmount",
            "params": {"token": {"map": "$.metadata.maps.tokens", "keyPath": "@.chainId"}},
        }
    )

    assert field is None
    assert any("$.metadata.maps.tokens" in message for message in error_messages(out))


def test_calldata_map_reference_is_rejected() -> None:
    field, out = convert(
        {
            "path": "data",
            "label": "Call",
            "format": "calldata",
            "params": {"callee": {"map": "$.metadata.maps.tokens", "keyPath": "@.chainId"}},
        }
    )

    assert field is None
    assert any('parameter "callee"' in message for message in error_messages(out))


def test_collection_map_reference_is_rejected() -> None:
    field, out = convert(
        {
            "path": "target",
            "label": "NFT",
            "format": "nftName",
            "params": {"collection": {"map": "$.metadata.maps.tokens", "keyPath": "@.chainId"}},
        }
    )

    assert field is None
    assert any('parameter "collection"' in message for message in error_messages(out))


def test_sender_address_map_reference_is_rejected() -> None:
    field, out = convert(
        {
            "path": "target",
            "label": "Target",
            "format": "addressName",
            "params": {"senderAddress": {"map": "$.metadata.maps.tokens", "keyPath": "@.chainId"}},
        }
    )

    assert field is None
    assert any('parameter "senderAddress"' in message for message in error_messages(out))


def test_token_amount_chain_id_path_is_ignored_with_a_warning() -> None:
    field, out = convert(
        {
            "path": "amount",
            "label": "Amount",
            "format": "tokenAmount",
            "params": {"tokenPath": "token", "chainIdPath": "chainId"},
        }
    )

    assert error_messages(out) == []
    assert field is not None
    assert field["assetPath"] == "token"
    assert [output.title for output in out.outputs if output.level == Output.Level.WARNING] == [
        "Chain ID not supported"
    ]
