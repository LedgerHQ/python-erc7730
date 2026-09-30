"""
Address checksum checks on the way from the input to the resolved descriptor.

An address written in a field is validated by the input model. An address that comes from a constant is only seen
by the resolver, so these tests go through the whole conversion.
"""

from typing import Any

import pytest

from erc7730.common.output import ListOutputAdder
from erc7730.convert.resolved.address import resolved_address
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

CHECKSUMMED = "0xb426b5AE61c23fF1B901a8AD1f1A3921D1E9D2F1"
WRONG_CHECKSUM = "0xb426B5aE61c23Ff1b901A8ad1F1A3921D1E9D2f1"


def _descriptor(constants: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """A contract descriptor with one token amount field, whose parameters may refer to the constants."""
    return {
        "context": {
            "$id": "test",
            "contract": {"deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}]},
        },
        "metadata": {"owner": "Test", "constants": constants},
        "display": {
            "formats": {
                "transfer(address to,uint256 amount)": {
                    "intent": "Transfer",
                    "fields": [{"path": "amount", "label": "Amount", "format": "tokenAmount", "params": params}],
                }
            }
        },
    }


def _convert(descriptor: dict[str, Any]) -> ListOutputAdder:
    out = ListOutputAdder()
    ERC7730InputToResolved().convert(InputERC7730Descriptor.model_validate(descriptor, strict=False), out)
    return out


@pytest.mark.parametrize("address", [CHECKSUMMED, CHECKSUMMED.lower()])
def test_resolved_address_accepted(address: str) -> None:
    out = ListOutputAdder()
    assert resolved_address(address, out) == address
    assert out.outputs == []


@pytest.mark.parametrize(
    "value,expected_error",
    [
        (WRONG_CHECKSUM, "invalid EIP-55 checksum"),
        ("0xb426", "expected a 20 bytes, hexadecimal Ethereum address"),
        (42, "expected a 20 bytes, hexadecimal Ethereum address"),
    ],
)
def test_resolved_address_rejected(value: object, expected_error: str) -> None:
    out = ListOutputAdder()
    assert resolved_address(value, out) is None
    assert [o.title for o in out.outputs] == ["Invalid address"]
    assert expected_error in out.outputs[0].message


@pytest.mark.parametrize("param", ["token", "nativeCurrencyAddress"])
def test_constant_address_accepted(param: str) -> None:
    out = _convert(_descriptor({"addr": CHECKSUMMED}, {param: "$.metadata.constants.addr"}))
    assert out.outputs == []


@pytest.mark.parametrize("param", ["token", "nativeCurrencyAddress"])
def test_constant_address_wrong_checksum(param: str) -> None:
    out = _convert(_descriptor({"addr": WRONG_CHECKSUM}, {param: "$.metadata.constants.addr"}))
    # the converter may add a generic error at the parameter after the specific one
    assert out.outputs[0].title == "Invalid address"
    assert "invalid EIP-55 checksum" in out.outputs[0].message
    assert CHECKSUMMED in out.outputs[0].message


def test_constant_address_in_list_wrong_checksum() -> None:
    out = _convert(
        _descriptor(
            {"addr": WRONG_CHECKSUM},
            {"nativeCurrencyAddress": ["0x0000000000000000000000000000000000000002", "$.metadata.constants.addr"]},
        )
    )
    assert out.outputs[0].title == "Invalid address"
    assert WRONG_CHECKSUM in out.outputs[0].message


def test_literal_address_wrong_checksum_rejected_by_model() -> None:
    with pytest.raises(ValueError, match="invalid EIP-55 checksum"):
        InputERC7730Descriptor.model_validate(_descriptor({}, {"token": WRONG_CHECKSUM}), strict=False)
