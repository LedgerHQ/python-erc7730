import json
from typing import Any

import pytest

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.convert.calldata.v1.tlv import CalldataDescriptorFieldTag, tlv_field
from erc7730.model.calldata.v1.instruction import CalldataDescriptorInstructionFieldV1
from erc7730.model.calldata.v1.param import (
    CalldataDescriptorDateType,
    CalldataDescriptorParamAmountV1,
    CalldataDescriptorParamCalldataV1,
    CalldataDescriptorParamDatetimeV1,
    CalldataDescriptorParamDurationV1,
    CalldataDescriptorParamEnumV1,
    CalldataDescriptorParamNetworkV1,
    CalldataDescriptorParamNFTV1,
    CalldataDescriptorParamRawV1,
    CalldataDescriptorParamTokenAmountV1,
    CalldataDescriptorParamTokenV1,
    CalldataDescriptorParamTrustedNameV1,
    CalldataDescriptorParamType,
    CalldataDescriptorParamUnitV1,
    CalldataDescriptorParamV1,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

DEFAULT_CHAIN_ID = 1
DEFAULT_ADDRESS = "0x0000000000000000000000000000000000000001"


def convert_field(
    signature: str,
    field: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
    chain_id: int = DEFAULT_CHAIN_ID,
) -> CalldataDescriptorInstructionFieldV1:
    """Build a minimal v2 descriptor around a single display field and return the converted calldata field."""
    meta: dict[str, Any] = {"owner": "Test Owner"}
    if metadata is not None:
        meta.update(metadata)

    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {"deployments": [{"chainId": chain_id, "address": DEFAULT_ADDRESS}]},
                },
                "metadata": meta,
                "display": {"formats": {signature: {"intent": "Test intent", "fields": [field]}}},
            }
        )
    )

    descriptors = erc7730_v2_descriptor_to_calldata_descriptors(descriptor, chain_id=chain_id)
    assert len(descriptors) == 1
    assert len(descriptors[0].fields) == 1
    return descriptors[0].fields[0]


def assert_serializes_param_type(
    field: CalldataDescriptorInstructionFieldV1,
    param_type: CalldataDescriptorParamType,
) -> None:
    """Assert the field TLV serialization carries the expected PARAM_TYPE tag / value."""
    tlv = tlv_field(field)
    assert bytes([CalldataDescriptorFieldTag.PARAM_TYPE, 0x01, param_type]) in tlv


# Homogeneous cases: signature + display field -> expected param class / param type.
FIELD_CASES: list[tuple[str, str, dict[str, Any], type[CalldataDescriptorParamV1], CalldataDescriptorParamType]] = [
    (
        "raw",
        "store(uint256 value)",
        {"path": "value", "label": "Value", "format": "raw"},
        CalldataDescriptorParamRawV1,
        CalldataDescriptorParamType.RAW,
    ),
    (
        "amount",
        "pay(uint256 amount)",
        {"path": "amount", "label": "Amount", "format": "amount"},
        CalldataDescriptorParamAmountV1,
        CalldataDescriptorParamType.AMOUNT,
    ),
    (
        "duration",
        "lock(uint256 period)",
        {"path": "period", "label": "Duration", "format": "duration"},
        CalldataDescriptorParamDurationV1,
        CalldataDescriptorParamType.DURATION,
    ),
    (
        "chainId",
        "bridge(uint256 chainId)",
        {"path": "chainId", "label": "Network", "format": "chainId"},
        CalldataDescriptorParamNetworkV1,
        CalldataDescriptorParamType.NETWORK,
    ),
    (
        "tokenTicker",
        "getTokenTicker(address token)",
        {"path": "token", "label": "Token", "format": "tokenTicker"},
        CalldataDescriptorParamTokenV1,
        CalldataDescriptorParamType.TOKEN,
    ),
    (
        "addressName",
        "transfer(address recipient)",
        {"path": "recipient", "label": "Recipient", "format": "addressName", "params": {"types": ["contract"]}},
        CalldataDescriptorParamTrustedNameV1,
        CalldataDescriptorParamType.TRUSTED_NAME,
    ),
    (
        "tokenAmount",
        "transfer(address token, uint256 amount)",
        {"path": "amount", "label": "Amount", "format": "tokenAmount", "params": {"tokenPath": "token"}},
        CalldataDescriptorParamTokenAmountV1,
        CalldataDescriptorParamType.TOKEN_AMOUNT,
    ),
    (
        "nftName",
        "transferNft(address collection, uint256 tokenId)",
        {"path": "tokenId", "label": "NFT", "format": "nftName", "params": {"collectionPath": "collection"}},
        CalldataDescriptorParamNFTV1,
        CalldataDescriptorParamType.NFT,
    ),
    (
        "calldata",
        "execute(address target, bytes data)",
        {"path": "data", "label": "Embedded call", "format": "calldata", "params": {"calleePath": "target"}},
        CalldataDescriptorParamCalldataV1,
        CalldataDescriptorParamType.CALLDATA,
    ),
    (
        "enum",
        "setMode(uint8 mode)",
        {"path": "mode", "label": "Mode", "format": "enum", "params": {"$ref": "$.metadata.enums.interestRateMode"}},
        CalldataDescriptorParamEnumV1,
        CalldataDescriptorParamType.ENUM,
    ),
]

_ENUM_METADATA = {"enums": {"interestRateMode": {"1": "stable", "2": "variable"}}}


@pytest.mark.parametrize(
    ("signature", "field", "param_class", "param_type"),
    [(sig, field, cls, ptype) for _, sig, field, cls, ptype in FIELD_CASES],
    ids=[case_id for case_id, *_ in FIELD_CASES],
)
def test_convert_field(
    signature: str,
    field: dict[str, Any],
    param_class: type[CalldataDescriptorParamV1],
    param_type: CalldataDescriptorParamType,
) -> None:
    metadata = _ENUM_METADATA if field["format"] == "enum" else None
    output = convert_field(signature, field, metadata=metadata)

    assert output.name == field["label"]
    assert isinstance(output.param, param_class)
    assert_serializes_param_type(output, param_type)


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [("timestamp", CalldataDescriptorDateType.UNIX), ("blockheight", CalldataDescriptorDateType.BLOCK_HEIGHT)],
)
def test_convert_date_encoding(encoding: str, expected: CalldataDescriptorDateType) -> None:
    field = convert_field(
        "schedule(uint256 deadline)",
        {"path": "deadline", "label": "Deadline", "format": "date", "params": {"encoding": encoding}},
    )

    assert isinstance(field.param, CalldataDescriptorParamDatetimeV1)
    assert field.param.date_type == expected
    assert_serializes_param_type(field, CalldataDescriptorParamType.DATETIME)


def test_convert_unit_params() -> None:
    field = convert_field(
        "setRate(uint256 rate)",
        {"path": "rate", "label": "Rate", "format": "unit", "params": {"base": "%", "decimals": 4, "prefix": False}},
    )

    assert isinstance(field.param, CalldataDescriptorParamUnitV1)
    assert field.param.base == "%"
    assert field.param.decimals == 4
    assert field.param.prefix is False


def test_convert_token_ticker_has_no_native_currencies() -> None:
    field = convert_field(
        "getTokenTicker(address token)",
        {"path": "token", "label": "Token", "format": "tokenTicker"},
    )

    assert isinstance(field.param, CalldataDescriptorParamTokenV1)
    assert field.param.native_currencies is None


def test_convert_token_amount_resolves_token_path() -> None:
    field = convert_field(
        "transfer(address token, uint256 amount)",
        {"path": "amount", "label": "Amount", "format": "tokenAmount", "params": {"tokenPath": "token"}},
    )

    assert isinstance(field.param, CalldataDescriptorParamTokenAmountV1)
    assert field.param.token is not None
