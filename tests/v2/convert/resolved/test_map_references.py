import json
from typing import Any

import pytest

from erc7730.common.output import ListOutputAdder
from erc7730.convert.ledger.eip712.convert_erc7730_v2_to_eip712 import ERC7730V2toEIP712Converter
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.display import ResolvedValueConstant
from erc7730.model.resolved.v2.display import ResolvedFieldDescription, ResolvedTokenAmountParameters

USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
DEPLOYMENT = {"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}


def map_ref(map_name: str, key_path: str) -> dict[str, str]:
    return {"map": f"$.metadata.maps.{map_name}", "keyPath": key_path}


def descriptor(
    signature: str,
    field: dict[str, Any],
    maps: dict[str, dict[str, Any]],
    *,
    eip712: bool = False,
    constants: dict[str, Any] | None = None,
) -> InputERC7730Descriptor:
    """Build a single deployment descriptor around a single display field, with the given maps."""
    context = (
        {"$id": "test", "eip712": {"domain": {"name": "Test"}, "deployments": [DEPLOYMENT]}}
        if eip712
        else {"$id": "test", "contract": {"deployments": [DEPLOYMENT]}}
    )
    return InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": context,
                "metadata": {
                    "owner": "Test Owner",
                    "constants": {"chain": 1} if constants is None else constants,
                    "maps": {name: {"values": values} for name, values in maps.items()},
                },
                "display": {"formats": {signature: {"intent": "Test intent", "fields": [field]}}},
            }
        )
    )


def token_amount_descriptor(token_map: dict[str, Any], key_path: str) -> InputERC7730Descriptor:
    return descriptor(
        "deposit(uint256 assets)",
        {
            "path": "assets",
            "label": "Deposit asset",
            "format": "tokenAmount",
            "params": {"token": map_ref("t", key_path)},
        },
        {"t": token_map},
    )


def resolve(input_descriptor: InputERC7730Descriptor) -> tuple[Any, list[str]]:
    out = ListOutputAdder()
    resolved = ERC7730InputToResolved().convert(input_descriptor, out)
    return resolved, [output.message for output in out.outputs]


def test_constant_key_missing_value_rejects_descriptor() -> None:
    # the field must not be emitted without its token
    resolved, messages = resolve(token_amount_descriptor({"8453": USDC}, "$.metadata.constants.chain"))

    assert resolved is None
    assert any('has no value for key "1"' in message for message in messages)


@pytest.mark.parametrize("flag", [True, False])
def test_constant_boolean_key(flag: bool) -> None:
    # JSON object keys are strings, a boolean key is written "true" or "false"
    other = "0x0000000000000000000000000000000000000002"
    resolved, messages = resolve(
        descriptor(
            "deposit(uint256 assets)",
            {
                "path": "assets",
                "label": "Deposit asset",
                "format": "tokenAmount",
                "params": {"token": map_ref("t", "$.metadata.constants.flag")},
            },
            {"t": {"true": USDC, "false": other}},
            constants={"flag": flag},
        )
    )

    assert resolved is not None, messages
    field = next(iter(resolved.display.formats.values())).fields[0]
    assert isinstance(field, ResolvedFieldDescription)
    assert isinstance(field.params, ResolvedTokenAmountParameters)
    assert isinstance(field.params.token, ResolvedValueConstant)
    assert field.params.token.value == (USDC if flag else other)


def test_sender_address_map_missing_value_rejects_descriptor() -> None:
    resolved, messages = resolve(
        descriptor(
            "transfer(address to)",
            {
                "path": "to",
                "label": "To",
                "format": "addressName",
                "params": {"types": ["eoa"], "senderAddress": map_ref("s", "$.metadata.constants.chain")},
            },
            {"s": {"8453": USDC}},
        )
    )

    assert resolved is None
    assert any('has no value for key "1"' in message for message in messages)


def test_calldata_optional_map_failure_rejects_descriptor() -> None:
    resolved, messages = resolve(
        descriptor(
            "execute(address target, bytes data)",
            {
                "path": "data",
                "label": "Embedded call",
                "format": "calldata",
                "params": {"calleePath": "target", "amount": map_ref("a", "$.metadata.constants.chain")},
            },
            {"a": {"8453": 1000}},
        )
    )

    assert resolved is None
    assert any('has no value for key "1"' in message for message in messages)


def test_map_address_value_must_be_20_bytes() -> None:
    resolved, messages = resolve(token_amount_descriptor({"1": "0x01"}, "@.chainId"))

    assert resolved is None
    assert any("is not a valid 20 bytes address" in message for message in messages)


def test_constant_key_only_encodes_selected_value() -> None:
    # the value for 8453 is not a valid address, but is never selected
    resolved, messages = resolve(token_amount_descriptor({"1": USDC, "8453": True}, "$.metadata.constants.chain"))

    assert resolved is not None, messages
    field = next(iter(resolved.display.formats.values())).fields[0]
    assert isinstance(field, ResolvedFieldDescription)
    assert isinstance(field.params, ResolvedTokenAmountParameters)
    assert isinstance(field.params.token, ResolvedValueConstant)
    assert field.params.token.value == USDC


def test_legacy_eip712_rejects_sender_address_map() -> None:
    out = ListOutputAdder()
    result = ERC7730V2toEIP712Converter().convert(
        descriptor(
            "Order(address owner,address to)",
            {
                "path": "to",
                "label": "To",
                "format": "addressName",
                "params": {"types": ["eoa"], "senderAddress": map_ref("s", "owner")},
            },
            {"s": {USDC: USDC}},
            eip712=True,
        ),
        out,
    )

    assert result is None
    assert any('Map lookup "senderAddress" of field "To"' in output.message for output in out.outputs)
