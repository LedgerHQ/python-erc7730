import json
from typing import Any

import pytest
from pydantic import ValidationError

from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

DEFAULT_CHAIN_ID = 1
DEFAULT_ADDRESS = "0x0000000000000000000000000000000000000001"


def load_field(field: dict[str, Any]) -> InputERC7730Descriptor:
    """Build a minimal v2 descriptor around a single display field and validate it."""
    return InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {"deployments": [{"chainId": DEFAULT_CHAIN_ID, "address": DEFAULT_ADDRESS}]},
                },
                "metadata": {"owner": "Test Owner"},
                "display": {"formats": {"store(bytes32 value)": {"intent": "Test intent", "fields": [field]}}},
            }
        )
    )


@pytest.mark.parametrize("iteration", ["sequential", "bundled"])
def test_field_group_accepts_schema_iteration_strategies(iteration: str) -> None:
    """The schema restricts iteration to "sequential" / "bundled"."""
    load_field({"path": "value", "iteration": iteration, "fields": [{"path": "value", "label": "V", "format": "raw"}]})


@pytest.mark.parametrize(
    "iteration",
    [
        pytest.param("Sequential", id="wrong-case"),
        pytest.param("parallel", id="unknown-strategy"),
        pytest.param("", id="empty"),
    ],
)
def test_field_group_rejects_unknown_iteration_strategy(iteration: str) -> None:
    """
    An unknown iteration strategy must be rejected rather than carried into the resolved descriptor.

    It is passed through conversion untouched, so an unnoticed typo reaches consumers as-is.
    """
    with pytest.raises(ValidationError):
        load_field(
            {"path": "value", "iteration": iteration, "fields": [{"path": "value", "label": "V", "format": "raw"}]}
        )


@pytest.mark.parametrize("format", ["addressName", "interoperableAddressName"])
@pytest.mark.parametrize("types", [["wallet"], ["eoa", "contract"], ["token"], ["collection"]])
def test_address_name_accepts_schema_address_types(format: str, types: list[str]) -> None:
    """
    Both address name formats carry the same address type enum in the schema.

    They also deserialize to the same parameters model, so this pins the behaviour of the pair rather
    than of either branch on its own.
    """
    load_field({"path": "value", "label": "Value", "format": format, "params": {"types": types}})


@pytest.mark.parametrize("format", ["addressName", "interoperableAddressName"])
@pytest.mark.parametrize(
    "types",
    [
        pytest.param(["person"], id="unknown-type"),
        pytest.param(["EOA"], id="wrong-case"),
        pytest.param(["wallet", "nft"], id="one-invalid-among-valid"),
    ],
)
def test_address_name_rejects_unknown_address_types(format: str, types: list[str]) -> None:
    """
    An address type outside the schema enum must be rejected for both address name formats.

    Wallets restrict name lookup on these values, so an unrecognized one silently widens what is trusted.
    Both formats deserialize to the same parameters model, so this pins the behaviour of the pair.
    """
    with pytest.raises(ValidationError):
        load_field({"path": "value", "label": "Value", "format": format, "params": {"types": types}})
