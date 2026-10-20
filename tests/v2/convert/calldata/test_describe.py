from typing import Any

import pytest
from pydantic_string_url import HttpUrl

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import _describe
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

SOURCE = HttpUrl("https://example.com/calldata-MyContract.json")


def descriptor(*, context_id: str | None = None, contract_name: str | None = None) -> InputERC7730Descriptor:
    context: dict[str, Any] = {
        "contract": {"deployments": [{"chainId": 1, "address": "0x0000000000000000000000000000000000000001"}]}
    }
    if context_id is not None:
        context["$id"] = context_id
    metadata: dict[str, Any] = {"owner": "Someone"}
    if contract_name is not None:
        metadata["contractName"] = contract_name
    return InputERC7730Descriptor.model_validate(
        {"context": context, "metadata": metadata, "display": {"formats": {}}}, strict=True
    )


def test_the_contract_name_is_preferred() -> None:
    assert _describe(descriptor(context_id="Fallback", contract_name="MyContract"), None) == "MyContract"


def test_the_context_id_is_the_fallback() -> None:
    """A descriptor need not set contractName, and $id is what the output falls back to as well."""
    assert _describe(descriptor(context_id="MyContract"), None) == "MyContract"


def test_a_source_is_kept_beside_the_name() -> None:
    """Both identify it, and a batch run over many files wants the path as well as the name."""
    assert _describe(descriptor(contract_name="MyContract"), SOURCE) == f"MyContract ({SOURCE})"


def test_the_source_alone_is_used_when_the_descriptor_names_nothing() -> None:
    assert _describe(descriptor(), SOURCE) == str(SOURCE)


def test_neither_is_stated_rather_than_printing_none() -> None:
    """The old message read "file None", which named nothing at all."""
    assert _describe(descriptor(), None) == "<unidentified>"


@pytest.mark.parametrize("source", [None, SOURCE])
def test_it_never_returns_none_as_text(source: HttpUrl | None) -> None:
    assert "None" not in _describe(descriptor(), source)
