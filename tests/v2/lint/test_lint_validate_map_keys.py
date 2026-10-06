import json

import pytest

from erc7730.common.output import ListOutputAdder
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint.v2.lint_validate_map_keys import ValidateMapKeysLinter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

TOKEN_A = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
TOKEN_B = "0xdAC17F958D2ee523a2206206994597C13D831ec7"


def lint(key_path: str, keys: list[str], signature: str = "deposit(uint256 assets, uint32 marketId)") -> list[str]:
    """Lint a descriptor looking up a token amount token in a map, with the given keys."""
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {
                        "deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}]
                    },
                },
                "metadata": {
                    "owner": "Test Owner",
                    "maps": {"tokens": {"values": dict(zip(keys, [TOKEN_A, TOKEN_B], strict=False))}},
                },
                "display": {
                    "formats": {
                        signature: {
                            "intent": "Deposit",
                            "fields": [
                                {
                                    "path": "assets",
                                    "label": "Amount",
                                    "format": "tokenAmount",
                                    "params": {"token": {"map": "$.metadata.maps.tokens", "keyPath": key_path}},
                                }
                            ],
                        }
                    }
                },
            }
        )
    )
    out = ListOutputAdder()
    resolved = ERC7730InputToResolved().convert(descriptor, out)
    assert resolved is not None, out.outputs
    ValidateMapKeysLinter().lint(descriptor, resolved, out)
    return [output.message for output in out.outputs]


def test_valid_keys() -> None:
    assert lint("#.marketId", ["1", "4294967295"]) == []


@pytest.mark.parametrize(
    "key_path,keys,expected",
    [
        ("#.marketId", ["1", "4294967296"], 'Key "4294967296" of map $.metadata.maps.tokens cannot be matched'),
        ("#.marketId", ["1", "foo"], 'Key "foo" of map $.metadata.maps.tokens cannot be matched'),
        ("#.marketId", ["1", "0x01"], 'Keys "1" and "0x01" of map $.metadata.maps.tokens encode to the same'),
        ("@.from", ["1", TOKEN_A], 'Key "1" of map $.metadata.maps.tokens cannot be matched'),
    ],
)
def test_invalid_keys(key_path: str, keys: list[str], expected: str) -> None:
    messages = lint(key_path, keys)
    assert any(expected in message for message in messages), messages


def test_reports_all_invalid_keys() -> None:
    messages = lint("#.marketId", ["4294967296", "foo"])
    assert len(messages) == 2, messages


def test_deployment_keys_not_checked() -> None:
    # keys of maps keyed on the chain id are checked against deployments during resolution
    assert lint("@.chainId", ["1", "foo"]) == []


def test_selector_format_key_not_checked() -> None:
    # without a declared signature, the key type is unknown
    assert lint("#.marketId", ["1", "4294967296"], signature="0xe2bbb158") == []


def test_format_without_map_lookup_not_converted_to_abi_tree() -> None:
    # fixed point numbers cannot be converted to an ABI tree, which must not fail descriptors that do not need it
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {
                        "deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}]
                    },
                },
                "metadata": {"owner": "Test Owner"},
                "display": {
                    "formats": {
                        "setRate(fixed128x18 rate)": {
                            "intent": "Set rate",
                            "fields": [{"path": "rate", "label": "Rate", "format": "raw"}],
                        }
                    }
                },
            }
        )
    )
    out = ListOutputAdder()
    resolved = ERC7730InputToResolved().convert(descriptor, out)
    assert resolved is not None, out.outputs
    ValidateMapKeysLinter().lint(descriptor, resolved, out)
    assert out.outputs == []
