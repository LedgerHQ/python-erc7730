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
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorTypeFamily,
    CalldataDescriptorValueConstantV1,
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
        "store(uint256 value)",
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
        "store(uint256 value)",
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
    ("signature", "value", "expected"),
    [
        # numbers are compared on 256 bits, so the narrowest encoding of the value is enough
        pytest.param("store(uint256 value)", 1, "0x01", id="uint"),
        pytest.param("store(uint256 value)", 256, "0x0100", id="uint-two-bytes"),
        pytest.param("store(uint256 value)", "0x0100", "0x0100", id="uint-hex"),
        pytest.param("store(int256 value)", 200, "0xc8", id="int-positive"),
        # the device only reads a constraint as signed when it is exactly as wide as the type
        pytest.param("store(int256 value)", -1, "0x" + "ff" * 32, id="int-negative"),
        pytest.param("store(int64 value)", -2, "0xfffffffffffffffe", id="int-negative-narrow"),
        # an address is right aligned on 20 bytes before comparison
        pytest.param(
            "store(address value)",
            "0x0000000000000000000000000000000000000020",
            "0x0000000000000000000000000000000000000020",
            id="address",
        ),
        # any non zero byte reads as true
        pytest.param("store(bool value)", True, "0x01", id="bool-true"),
        pytest.param("store(bool value)", False, "0x00", id="bool-false"),
        # a static bytesN sits left aligned in its 32 byte calldata chunk, and the device compares
        # the whole chunk, so the constraint carries the same ABI padding
        pytest.param("store(bytes32 value)", "0x40", "0x40" + "00" * 31, id="bytes32-padded"),
        pytest.param("store(bytes4 value)", "0xa9059cbb", "0xa9059cbb" + "00" * 28, id="bytes4-padded"),
        # a dynamic bytes has no width at conversion time, so it is left as written
        pytest.param("store(bytes value)", "0xdeadbeef", "0xdeadbeef", id="bytes-dynamic"),
        # a string carries its text in calldata, so a "0x" prefixed value is that text, not a payload
        pytest.param("store(string value)", "hello", "0x68656c6c6f", id="string-utf8"),
        pytest.param("store(string value)", "0x40", "0x30783430", id="string-looking-like-hex"),
        # and it is not hexadecimal either, so it must not be parsed as such
        pytest.param("store(string value)", "0xhello", "0x307868656c6c6f", id="string-not-valid-hex"),
        # the widest value each narrow type can actually hold is still a usable constraint
        pytest.param("store(uint8 value)", 255, "0xff", id="uint8-max"),
        pytest.param("store(int8 value)", 127, "0x7f", id="int8-max"),
        pytest.param("store(int8 value)", -128, "0x80", id="int8-min"),
        pytest.param("store(int16 value)", 32767, "0x7fff", id="int16-max"),
    ],
)
def test_convert_constraint_value_encoding(signature: str, value: Any, expected: str) -> None:
    """
    Constraint values are encoded for the type family of the value the device formatter reads.

    The JSON type they are written with is not enough: the device compares numerically for integers,
    right aligned on 20 bytes for addresses, and byte for byte for bytes and strings, so the same
    JSON value has to be encoded differently depending on the field it constrains.
    """
    field = convert_field(
        signature,
        {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": [value]}},
    )

    assert field.constraints == [expected]


@pytest.mark.parametrize(
    ("signature", "value"),
    [
        # an integer on a bytes field encodes to a payload narrower than the value, which the device
        # can never match, so it must not reach a descriptor
        pytest.param("store(bytes32 value)", 1, id="int-on-bytes"),
        pytest.param("store(bytes32 value)", True, id="bool-on-bytes"),
        pytest.param("store(bytes32 value)", "hello", id="text-on-bytes"),
        pytest.param("store(bytes4 value)", "0x" + "11" * 8, id="hex-wider-than-bytes-field"),
        pytest.param("store(uint256 value)", -1, id="negative-on-unsigned"),
        pytest.param("store(uint256 value)", "hello", id="text-on-uint"),
        pytest.param("store(address value)", 32, id="int-on-address"),
        pytest.param("store(address value)", "0x" + "11" * 32, id="hex-wider-than-address"),
        pytest.param("store(bool value)", 2, id="non-boolean-on-bool"),
        pytest.param("store(string value)", 1, id="int-on-string"),
        # a value the field is too narrow to ever hold can never match, whether written as a number
        # or as a payload
        pytest.param("store(uint8 value)", 256, id="over-width-on-uint8"),
        pytest.param("store(uint8 value)", "0x0100", id="over-width-hex-on-uint8"),
        pytest.param("store(uint16 value)", 70000, id="over-width-on-uint16"),
        pytest.param("store(int16 value)", 32768, id="over-width-on-int16"),
        pytest.param("store(int8 value)", -129, id="under-width-on-int8"),
        pytest.param("store(int8 value)", "0x0100", id="over-width-hex-on-int8"),
    ],
)
def test_convert_rejects_constraint_values_the_device_cannot_match(signature: str, value: Any) -> None:
    """
    A constraint the device can never compare equal turns the rule off silently.

    A "mustMatch" that matches nothing would reject every transaction, and an "ifNotIn" that matches
    nothing would display the field it was meant to hide, so these are rejected at build time.
    """
    assert (
        convert_descriptor(
            signature,
            {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": [value]}},
        )
        == []
    )


@pytest.mark.parametrize(
    "format",
    [
        pytest.param("amount", id="amount"),
        pytest.param("duration", id="duration"),
        pytest.param("date", id="date"),
    ],
)
def test_convert_rejects_visibility_conditions_on_unsupported_formats(format: str) -> None:
    """
    Only the RAW and TRUSTED_NAME formatters read FIELD->VISIBLE on the device.

    Every other formatter ignores the tag, so emitting it would display a field meant to stay hidden
    and leave a "mustMatch" guard unenforced.
    """
    field: dict[str, Any] = {
        "path": "value",
        "label": "Value",
        "format": format,
        "visible": {"mustMatch": [1]},
    }
    if format == "date":
        field["params"] = {"encoding": "timestamp"}

    assert convert_descriptor("store(uint256 value)", field) == []


def test_convert_visibility_conditions_on_trusted_name_are_addresses() -> None:
    """
    The TRUSTED_NAME formatter resolves the value to an address before comparing constraints.

    So a constraint on such a field is an address whatever the ABI type of the field, and is left
    unpadded because the device right aligns it on 20 bytes.
    """
    field = convert_field(
        "store(bytes32 value)",
        {
            "path": "value",
            "label": "Value",
            "format": "addressName",
            "params": {"types": ["eoa"]},
            "visible": {"mustMatch": ["0x0000000000000000000000000000000000000020"]},
        },
    )

    assert field.constraints == ["0x0000000000000000000000000000000000000020"]


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(["0x01", "0x02", "0x03", "0x04", "0x05", "0x06"], id="too-many"),
        pytest.param([1.5], id="float"),
        pytest.param([None], id="null"),
    ],
)
def test_convert_rejects_invalid_constraint_values(values: list[Any]) -> None:
    """Values the device cannot compare, or more than it can store, are rejected at build time."""
    assert (
        convert_descriptor(
            "store(uint256 value)",
            {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": values}},
        )
        == []
    )


def test_convert_rejects_positive_int_the_field_reads_back_as_negative() -> None:
    """
    A positive value an "intN" cannot hold would be emitted with the sign bit set.

    The device reads a constraint as signed as soon as it is exactly as wide as the type, so 128 on
    an "int8" would be compared as -128: the emitted constraint would not mean what the descriptor
    says, and would collide with the constraint written as -128.
    """
    assert (
        convert_descriptor(
            "store(int8 value)",
            {"path": "value", "label": "Value", "format": "raw", "visible": {"mustMatch": [128]}},
        )
        == []
    )


@pytest.mark.parametrize(
    "constraint",
    [
        pytest.param("0x123", id="three-digits"),
        pytest.param("0x1", id="one-digit"),
    ],
)
def test_field_rejects_constraint_with_odd_number_of_hex_digits(constraint: str) -> None:
    """
    A constraint is a byte array, so it cannot carry half a byte.

    An odd number of digits otherwise passes validation and only fails when the FIELD struct is
    serialized, which is far from the descriptor that caused it.
    """
    param = CalldataDescriptorParamRawV1(
        value=CalldataDescriptorValueConstantV1(
            type_family=CalldataDescriptorTypeFamily.UINT, type_size=1, value=1, raw="0x01"
        )
    )

    with pytest.raises(ValidationError, match="whole bytes"):
        CalldataDescriptorInstructionFieldV1(
            name="Value",
            param=param,
            visibility=CalldataDescriptorFieldVisibilityV1.MUST_BE,
            constraints=[constraint],
        )
