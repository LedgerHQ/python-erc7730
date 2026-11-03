from typing import Any

import pytest
from pydantic import ValidationError

from erc7730.common.output import ListOutputAdder
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.resolved.v2.display import ResolvedCallDataParameters, ResolvedFieldDescription
from tests.v2.model.test_enum_constraints import load_field


def _calldata_field(**params: Any) -> dict[str, Any]:
    return {"path": "value", "label": "Call", "format": "calldata", "params": {"calleePath": "value", **params}}


def test_calldata_accepts_chain_id() -> None:
    load_field(_calldata_field(chainId=8453))


def test_calldata_accepts_chain_id_path() -> None:
    load_field(_calldata_field(chainIdPath="value"))


def test_calldata_rejects_chain_id_and_chain_id_path() -> None:
    with pytest.raises(ValidationError):
        load_field(_calldata_field(chainId=8453, chainIdPath="value"))


def test_calldata_chain_id_is_resolved() -> None:
    out = ListOutputAdder()
    resolved = ERC7730InputToResolved().convert(load_field(_calldata_field(chainId=8453)), out)
    assert resolved is not None
    field = next(iter(resolved.display.formats.values())).fields[0]
    assert isinstance(field, ResolvedFieldDescription)
    assert isinstance(field.params, ResolvedCallDataParameters)
    assert field.params.chainId is not None
    assert field.params.chainId.value == 8453  # type: ignore[union-attr]
