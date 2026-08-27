import json
from typing import Any

import pytest
from pydantic import ValidationError

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.convert.calldata.v1.tlv import CalldataDescriptorFieldTag, tlv_field
from erc7730.model.calldata.v1.instruction import (
    CalldataDescriptorFieldVisibilityV1,
    CalldataDescriptorInstructionFieldV1,
)
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


def convert_descriptor(signature: str, field: dict[str, Any]) -> list[Any]:
    """Build a minimal v2 descriptor around a single display field and return the raw conversion result."""
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {"deployments": [{"chainId": DEFAULT_CHAIN_ID, "address": DEFAULT_ADDRESS}]},
                },
                "metadata": {"owner": "Test Owner"},
                "display": {"formats": {signature: {"intent": "Test intent", "fields": [field]}}},
            }
        )
    )
    return erc7730_v2_descriptor_to_calldata_descriptors(descriptor, chain_id=DEFAULT_CHAIN_ID)


def parse_tlv(payload: bytes) -> list[tuple[int, bytes]]:
    """Parse a TLV payload into (tag, value) records, following the DER tag / length encoding."""

    def read_der(index: int) -> tuple[int, int]:
        if payload[index] == 0x81:
            return payload[index + 1], index + 2
        return payload[index], index + 1

    records: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(payload):
        tag, offset = read_der(offset)
        length, offset = read_der(offset)
        records.append((tag, payload[offset : offset + length]))
        offset += length
    return records


@pytest.mark.parametrize(
    ("visible", "expected_visibility"),
    [
        pytest.param({"mustMatch": ["0x40"]}, CalldataDescriptorFieldVisibilityV1.MUST_BE, id="mustMatch"),
        pytest.param({"ifNotIn": ["0x40"]}, CalldataDescriptorFieldVisibilityV1.IF_NOT_IN, id="ifNotIn"),
    ],
)
def test_convert_visibility_conditions(
    visible: dict[str, Any], expected_visibility: CalldataDescriptorFieldVisibilityV1
) -> None:
    """Visibility conditions map onto the FIELD VISIBLE / CONSTRAINT tags."""
    field = convert_field(
        "store(bytes32 value)",
        {"path": "value", "label": "Value", "format": "raw", "visible": visible},
    )

    assert field.visibility == expected_visibility
    assert field.constraints == ["0x40"]

    tags = [tag for tag, _ in parse_tlv(tlv_field(field))]
    values = dict(parse_tlv(tlv_field(field)))
    assert values[CalldataDescriptorFieldTag.VISIBLE] == bytes([expected_visibility.value])
    assert values[CalldataDescriptorFieldTag.CONSTRAINT] == bytes([0x40])
    # the device rejects a CONSTRAINT served before its VISIBLE tag
    assert tags.index(CalldataDescriptorFieldTag.VISIBLE) < tags.index(CalldataDescriptorFieldTag.CONSTRAINT)


def test_convert_rejects_both_visibility_conditions() -> None:
    """
    "ifNotIn" and "mustMatch" are mutually exclusive in the schema, so both set must not be accepted.

    The converter picks "mustMatch" when both are present, which would silently drop the "ifNotIn" rule.
    """
    with pytest.raises(ValidationError, match="mutually exclusive"):
        convert_field(
            "store(bytes32 value)",
            {
                "path": "value",
                "label": "Value",
                "format": "raw",
                "visible": {"ifNotIn": ["0x40"], "mustMatch": ["0xc0"]},
            },
        )


@pytest.mark.parametrize(
    "visible",
    [
        pytest.param("nver", id="typo"),
        pytest.param("hidden", id="unknown-rule"),
        pytest.param("Always", id="wrong-case"),
    ],
)
def test_convert_rejects_unknown_simple_visibility_rule(visible: str) -> None:
    """
    The schema restricts simple rules to "always" / "never" / "optional", so anything else must be rejected.

    A typo in "never" would otherwise be read as the default and display a field meant to stay hidden.
    """
    with pytest.raises(ValidationError):
        convert_field("store(bytes32 value)", {"path": "value", "label": "Value", "format": "raw", "visible": visible})


def test_convert_optional_visibility_is_displayed() -> None:
    """The v1 protocol has no optional visibility, so "optional" fields are displayed unconditionally."""
    field = convert_field(
        "store(bytes32 value)", {"path": "value", "label": "Value", "format": "raw", "visible": "optional"}
    )

    assert field.visibility == CalldataDescriptorFieldVisibilityV1.ALWAYS
    assert field.constraints is None


def test_convert_multiple_constraints_are_serialized_in_order() -> None:
    """CONSTRAINT may repeat, with OR semantics on the device."""
    field = convert_field(
        "store(bytes32 value)",
        {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": ["0x40", "0xc0"]}},
    )

    assert field.constraints == ["0x40", "0xc0"]
    constraints = [value for tag, value in parse_tlv(tlv_field(field)) if tag == CalldataDescriptorFieldTag.CONSTRAINT]
    assert constraints == [bytes([0x40]), bytes([0xC0])]


def test_convert_always_visible_field_omits_visible_tag() -> None:
    """VISIBLE defaults to ALWAYS on the device, so it is omitted to keep payloads stable."""
    field = convert_field("store(bytes32 value)", {"path": "value", "label": "Value", "format": "raw"})

    assert field.visibility == CalldataDescriptorFieldVisibilityV1.ALWAYS
    assert field.constraints is None
    tags = [tag for tag, _ in parse_tlv(tlv_field(field))]
    assert CalldataDescriptorFieldTag.VISIBLE not in tags
    assert CalldataDescriptorFieldTag.CONSTRAINT not in tags


def test_convert_mustmatch_field_without_label_uses_id() -> None:
    """A mustMatch field is never displayed so its label may be omitted, but NAME is mandatory."""
    field = convert_field(
        "store(bytes32 value)",
        {"$id": "valueGuard", "path": "value", "format": "raw", "visible": {"mustMatch": ["0x40"]}},
    )

    assert field.name == "valueGuard"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            "0x0000000000000000000000000000000000000020",
            "0x0000000000000000000000000000000000000020",
            id="hex-width-preserved",
        ),
        pytest.param(1, "0x01", id="int"),
        pytest.param(256, "0x0100", id="int-two-bytes"),
        pytest.param(True, "0x01", id="bool"),
        pytest.param("hello", "0x68656c6c6f", id="string-utf8"),
    ],
)
def test_convert_constraint_value_encoding(value: Any, expected: str) -> None:
    """
    Constraint values are emitted as raw bytes. Hex values keep their width because the device
    compares bytes and strings byte for byte, so a narrower constraint would never match.
    """
    field = convert_field(
        "store(bytes32 value)",
        {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": [value]}},
    )

    assert field.constraints == [expected]


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(["0x01", "0x02", "0x03", "0x04", "0x05", "0x06"], id="too-many"),
        pytest.param([-1], id="negative"),
        pytest.param([1.5], id="float"),
        pytest.param([None], id="null"),
    ],
)
def test_convert_rejects_invalid_constraint_values(values: list[Any]) -> None:
    """Values the device cannot compare, or more than it can store, are rejected at build time."""
    assert (
        convert_descriptor(
            "store(bytes32 value)",
            {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": values}},
        )
        == []
    )
