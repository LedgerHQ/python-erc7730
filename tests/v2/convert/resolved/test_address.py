"""
Address checksum checks on the way from the input to the resolved descriptor.

An address written in a parameter is validated by the input model. An address that comes from a constant, or that is
the literal value of a field, is only seen by the resolver, so these tests go through the whole conversion.
"""

from typing import Any

import pytest

from erc7730.common.output import ListOutputAdder
from erc7730.convert.resolved.v2.address import resolved_address, resolved_addresses
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

CHECKSUMMED = "0xb426b5AE61c23fF1B901a8AD1f1A3921D1E9D2F1"
WRONG_CHECKSUM = "0xb426B5aE61c23Ff1b901A8ad1F1A3921D1E9D2f1"
OTHER_WRONG_CHECKSUM = "0xDAC17F958D2ee523a2206206994597C13D831ec7"

# an ERC-7930 interoperable address: longer than 20 bytes, so not an address for the checksum check
INTEROPERABLE_ADDRESS = "0x00010000010114dac17f958d2ee523a2206206994597c13d831ec7"

# fields with an address parameter, written with a path to the constant `addr`
CONSTANT = "$.metadata.constants.addr"
FIELDS_WITH_ADDRESS_PARAMETER = {
    "token": {"path": "amount", "format": "tokenAmount", "params": {"token": CONSTANT}},
    "nativeCurrencyAddress": {"path": "amount", "format": "tokenAmount", "params": {"nativeCurrencyAddress": CONSTANT}},
    "senderAddress": {"path": "to", "format": "addressName", "params": {"senderAddress": CONSTANT}},
    "callee": {"path": "data", "format": "calldata", "params": {"callee": CONSTANT}},
    "spender": {"path": "data", "format": "calldata", "params": {"callee": CHECKSUMMED, "spender": CONSTANT}},
    "collection": {"path": "amount", "format": "nftName", "params": {"collection": CONSTANT}},
}

# formats whose field value is an address
ADDRESS_FORMATS: dict[str, dict[str, Any]] = {
    "addressName": {"format": "addressName", "params": {"types": ["eoa"]}},
    "tokenTicker": {"format": "tokenTicker"},
}


def _descriptor(field: dict[str, Any], constants: dict[str, Any] | None = None) -> dict[str, Any]:
    """A contract descriptor with one field, which may refer to the constants."""
    return {
        "context": {
            "$id": "test",
            "contract": {"deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}]},
        },
        "metadata": {"owner": "Test", "constants": constants or {}},
        "display": {
            "formats": {
                "transfer(address to,uint256 amount,bytes data)": {
                    "intent": "Transfer",
                    "fields": [{"label": "Field", **field}],
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


def test_resolved_addresses_accepted() -> None:
    out = ListOutputAdder()
    assert resolved_addresses([CHECKSUMMED, CHECKSUMMED.lower()], out) == [CHECKSUMMED, CHECKSUMMED.lower()]
    assert out.outputs == []


def test_resolved_addresses_stops_at_first_error() -> None:
    out = ListOutputAdder()
    assert resolved_addresses([CHECKSUMMED, WRONG_CHECKSUM, OTHER_WRONG_CHECKSUM], out) is None
    assert len(out.outputs) == 1
    assert WRONG_CHECKSUM in out.outputs[0].message


@pytest.mark.parametrize("param", FIELDS_WITH_ADDRESS_PARAMETER)
def test_constant_address_accepted(param: str) -> None:
    out = _convert(_descriptor(FIELDS_WITH_ADDRESS_PARAMETER[param], {"addr": CHECKSUMMED}))
    assert out.outputs == []


@pytest.mark.parametrize("param", FIELDS_WITH_ADDRESS_PARAMETER)
def test_constant_address_wrong_checksum(param: str) -> None:
    out = _convert(_descriptor(FIELDS_WITH_ADDRESS_PARAMETER[param], {"addr": WRONG_CHECKSUM}))
    # the converter may add a generic error at the parameter after the specific one
    assert out.outputs[0].title == "Invalid address"
    assert "invalid EIP-55 checksum" in out.outputs[0].message
    assert CHECKSUMMED in out.outputs[0].message


def test_constant_address_in_list_wrong_checksum() -> None:
    field = {
        "path": "amount",
        "format": "tokenAmount",
        "params": {"nativeCurrencyAddress": ["0x0000000000000000000000000000000000000002", CONSTANT]},
    }
    out = _convert(_descriptor(field, {"addr": WRONG_CHECKSUM}))
    assert out.outputs[0].title == "Invalid address"
    assert WRONG_CHECKSUM in out.outputs[0].message


def test_literal_parameter_wrong_checksum_rejected_by_model() -> None:
    field = {"path": "amount", "format": "tokenAmount", "params": {"token": WRONG_CHECKSUM}}
    with pytest.raises(ValueError, match="invalid EIP-55 checksum"):
        InputERC7730Descriptor.model_validate(_descriptor(field), strict=False)


@pytest.mark.parametrize("fmt", ADDRESS_FORMATS)
@pytest.mark.parametrize("value", [WRONG_CHECKSUM, CONSTANT])
def test_field_value_wrong_checksum(fmt: str, value: str) -> None:
    """The value of a field is a scalar for the input model, so only the resolver can check it."""
    out = _convert(_descriptor({"value": value, **ADDRESS_FORMATS[fmt]}, {"addr": WRONG_CHECKSUM}))
    assert out.outputs[0].title == "Invalid address"
    assert "invalid EIP-55 checksum" in out.outputs[0].message


@pytest.mark.parametrize("fmt", ADDRESS_FORMATS)
@pytest.mark.parametrize("value", [CHECKSUMMED, CONSTANT])
def test_field_value_accepted(fmt: str, value: str) -> None:
    out = _convert(_descriptor({"value": value, **ADDRESS_FORMATS[fmt]}, {"addr": CHECKSUMMED}))
    assert out.outputs == []


@pytest.mark.parametrize("value", [INTEROPERABLE_ADDRESS, CONSTANT])
def test_interoperable_address_value_is_not_checked(value: str) -> None:
    field = {"value": value, "format": "interoperableAddressName", "params": {"types": ["eoa"]}}
    out = _convert(_descriptor(field, {"addr": INTEROPERABLE_ADDRESS}))
    assert out.outputs == []
