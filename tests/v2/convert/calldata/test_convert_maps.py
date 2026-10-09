"""
Tests for map lookups the device does itself: MAP_REF values, and the MAP_ENTRY structs carrying the map values.

Expected encodings follow app-ethereum (doc/tlv_structs.md#map_entry, src/features/provide_map_entry and
src/features/generic_tx_parser/gtp_value.c): the device reads the key from the transaction, then looks up the MAP_ENTRY
whose key matches it byte for byte.
"""

import json
from typing import Any

import pytest

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.convert.calldata.v1.tlv import tlv_value
from erc7730.model.calldata.v1.descriptor import CalldataDescriptorV1
from erc7730.model.calldata.v1.param import (
    CalldataDescriptorParamCalldataV1,
    CalldataDescriptorParamNFTV1,
    CalldataDescriptorParamTokenAmountV1,
)
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorContainerPathV1,
    CalldataDescriptorContainerPathValueV1,
    CalldataDescriptorDataPathV1,
    CalldataDescriptorTypeFamily,
    CalldataDescriptorValueConstantV1,
    CalldataDescriptorValueMapRefV1,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

ADDRESS = "0x0000000000000000000000000000000000000001"
OTHER_ADDRESS = "0x0000000000000000000000000000000000000002"
TOKEN_A = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
TOKEN_B = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

DEPOSIT = "deposit(uint256 assets, uint256 marketId)"
DEPOSIT_SELECTOR = "0xe2bbb158"


def map_ref(map_name: str, key_path: str) -> dict[str, str]:
    return {"map": f"$.metadata.maps.{map_name}", "keyPath": key_path}


def token_amount(key_path: str, map_name: str = "tokens", path: str = "assets") -> dict[str, Any]:
    return {"path": path, "label": "Amount", "format": "tokenAmount", "params": {"token": map_ref(map_name, key_path)}}


def convert(
    signature: str,
    fields: list[dict[str, Any]],
    maps: dict[str, dict[str, Any]],
    deployments: list[dict[str, Any]] | None = None,
) -> list[CalldataDescriptorV1]:
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "contract": {"deployments": deployments or [{"chainId": 1, "address": ADDRESS}]},
                },
                "metadata": {"owner": "Test Owner", "maps": {name: {"values": v} for name, v in maps.items()}},
                "display": {"formats": {signature: {"intent": "Test intent", "fields": fields}}},
            }
        )
    )
    return erc7730_v2_descriptor_to_calldata_descriptors(descriptor)


def convert_one(signature: str, fields: list[dict[str, Any]], maps: dict[str, dict[str, Any]]) -> CalldataDescriptorV1:
    descriptors = convert(signature, fields, maps)
    assert len(descriptors) == 1
    return descriptors[0]


def entries(descriptor: CalldataDescriptorV1) -> list[tuple[int, str, str]]:
    return [(entry.id, entry.key, entry.value) for entry in descriptor.maps]


def word(value: int) -> str:
    return "0x" + value.to_bytes(32, "big").hex()


def test_data_keyed_map_is_looked_up_by_the_device() -> None:
    descriptor = convert_one(DEPOSIT, [token_amount("marketId")], {"tokens": {"1": TOKEN_A, "42": TOKEN_B}})

    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamTokenAmountV1)
    token = param.token
    assert isinstance(token, CalldataDescriptorValueMapRefV1)
    assert token.type_family == CalldataDescriptorTypeFamily.ADDRESS
    assert token.type_size == 20
    assert token.map_ref.version == 1
    assert token.map_ref.id == 0
    assert token.map_ref.map == "$.metadata.maps.tokens"
    assert isinstance(token.map_ref.key.binary_path, CalldataDescriptorDataPathV1)
    assert token.map_ref.key.type_family == CalldataDescriptorTypeFamily.UINT

    # a uint256 calldata key is read as its whole ABI encoded chunk
    assert entries(descriptor) == [(0, word(1), TOKEN_A.lower()), (0, word(42), TOKEN_B.lower())]
    for entry in descriptor.maps:
        assert (entry.chain_id, entry.address, entry.selector) == (1, ADDRESS, DEPOSIT_SELECTOR)
    assert [(entry.key_source, entry.value_source) for entry in descriptor.maps] == [("1", TOKEN_A), ("42", TOKEN_B)]


def test_map_ref_value_tlv() -> None:
    descriptor = convert_one(DEPOSIT, [token_amount("marketId")], {"tokens": {"1": TOKEN_A}})
    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamTokenAmountV1)
    token = param.token
    assert isinstance(token, CalldataDescriptorValueMapRefV1)

    key = tlv_value(token.map_ref.key)
    # key: VALUE(version 1, UINT, size 32, DATA_PATH(version 1, TUPLE 1, LEAF STATIC))
    assert key.hex() == "000101" + "010101" + "020120" + "030a" + "000101" + "01020001" + "040103"

    map_ref = "000101" + "010100" + "02" + f"{len(key):02x}" + key.hex()
    assert tlv_value(token).hex() == "000101" + "010105" + "020114" + "06" + f"{len(map_ref) // 2:02x}" + map_ref

    # the field hash in TRANSACTION_INFO covers the MAP_REF
    assert tlv_value(token).hex() in descriptor.fields[0].descriptor


def test_map_entry_tlv() -> None:
    descriptor = convert_one(DEPOSIT, [token_amount("marketId")], {"tokens": {"175676": TOKEN_A}})

    # MAP_ENTRY version is 1 (STRUCT_VERSION in map_entry.c), the signature is appended by CAL
    assert descriptor.maps[0].descriptor == (
        "000101"
        + "01080000000000000001"
        + "0214"
        + ADDRESS[2:]
        + "0304"
        + DEPOSIT_SELECTOR[2:]
        + "040100"
        + "0520"
        + (175676).to_bytes(32, "big").hex()
        + "0614"
        + TOKEN_A[2:].lower()
    )


def test_map_entries_are_bound_to_each_deployment() -> None:
    descriptors = convert(
        DEPOSIT,
        [token_amount("marketId")],
        {"tokens": {"1": TOKEN_A}},
        deployments=[{"chainId": 1, "address": ADDRESS}, {"chainId": 8453, "address": OTHER_ADDRESS}],
    )

    assert [(d.maps[0].chain_id, d.maps[0].address) for d in descriptors] == [(1, ADDRESS), (8453, OTHER_ADDRESS)]


@pytest.mark.parametrize(
    ("signature", "key_path", "key", "expected"),
    [
        # static calldata values are read as their whole ABI encoded chunk
        ("f(uint256 assets, uint8 k)", "k", "0x2a", word(42)),
        ("f(uint256 assets, int16 k)", "k", "-2", "0x" + (-2).to_bytes(32, "big", signed=True).hex()),
        ("f(uint256 assets, bool k)", "k", "true", word(1)),
        ("f(uint256 assets, address k)", "k", TOKEN_A, "0x" + "00" * 12 + TOKEN_A[2:].lower()),
        ("f(uint256 assets, bytes4 k)", "k", "0x12345678", "0x12345678" + "00" * 28),
        # dynamic calldata values are read as their raw content
        ("f(uint256 assets, string k)", "k", "USDC", "0x" + b"USDC".hex()),
        ("f(uint256 assets, bytes k)", "k", "0xabcd", "0xabcd"),
        # sliced values are read as the slice
        ("f(uint256 assets, bytes k)", "k.[0:4]", "0xa9059cbb", "0xa9059cbb"),
        ("f(uint256 assets, uint256 k)", "k.[-20:]", TOKEN_A, TOKEN_A.lower()),
        ("f(uint256 assets, uint256 k)", "k.[-2:]", "258", "0x0102"),
        # values from the transaction context
        ("f(uint256 assets)", "@.from", TOKEN_A, TOKEN_A.lower()),
        ("f(uint256 assets)", "@.value", "1000", word(1000)),
    ],
)
def test_map_key_encoding(signature: str, key_path: str, key: str, expected: str) -> None:
    descriptor = convert_one(signature, [token_amount(key_path)], {"tokens": {key: TOKEN_A}})

    assert entries(descriptor) == [(0, expected, TOKEN_A.lower())]


def test_container_keyed_map_reads_container_value() -> None:
    descriptor = convert_one(DEPOSIT, [token_amount("@.from")], {"tokens": {TOKEN_B: TOKEN_A}})

    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamTokenAmountV1)
    assert isinstance(param.token, CalldataDescriptorValueMapRefV1)
    assert param.token.map_ref.key.binary_path == CalldataDescriptorContainerPathV1(
        value=CalldataDescriptorContainerPathValueV1.FROM
    )


@pytest.mark.parametrize("key_path", ["@.chainId", "@.to"])
def test_deployment_keyed_map_is_folded_into_a_constant(key_path: str) -> None:
    # the descriptor is bound to a single deployment, so there is nothing to look up on the device
    descriptor = convert_one(DEPOSIT, [token_amount(key_path)], {"tokens": {"1": TOKEN_A, ADDRESS: TOKEN_A}})

    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamTokenAmountV1)
    assert isinstance(param.token, CalldataDescriptorValueConstantV1)
    assert descriptor.maps == []


def test_map_used_twice_shares_its_entries() -> None:
    descriptor = convert_one(
        DEPOSIT,
        [token_amount("marketId"), token_amount("marketId", path="marketId")],
        {"tokens": {"1": TOKEN_A}},
    )

    assert entries(descriptor) == [(0, word(1), TOKEN_A.lower())]


def test_map_used_with_another_encoding_gets_another_id() -> None:
    # the same map keyed on a uint8 is read the same way, keyed on a string it is not
    descriptor = convert_one(
        "f(uint256 assets, uint256 a, uint8 b, string c)",
        [token_amount("a"), token_amount("b", path="b"), token_amount("c", path="a")],
        {"tokens": {"1": TOKEN_A}},
    )

    assert entries(descriptor) == [(0, word(1), TOKEN_A.lower()), (1, "0x31", TOKEN_A.lower())]
    ids = [field.param.token.map_ref.id for field in descriptor.fields]  # type: ignore[union-attr]
    assert ids == [0, 0, 1]


def test_maps_in_calldata_parameters() -> None:
    descriptor = convert_one(
        "execute(uint256 route, bytes data)",
        [
            {
                "path": "data",
                "label": "Call",
                "format": "calldata",
                "params": {
                    "callee": map_ref("targets", "route"),
                    "selector": map_ref("selectors", "route"),
                    "amount": map_ref("amounts", "route"),
                    "spender": map_ref("targets", "route"),
                },
            }
        ],
        {"targets": {"7": TOKEN_A}, "selectors": {"7": "0xa9059cbb"}, "amounts": {"7": 1000}},
    )

    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamCalldataV1)
    values = [param.callee, param.selector, param.amount, param.spender]
    assert all(isinstance(value, CalldataDescriptorValueMapRefV1) for value in values)
    assert [value.map_ref.id for value in values] == [0, 1, 2, 0]  # type: ignore[union-attr]
    assert entries(descriptor) == [
        (0, word(7), TOKEN_A.lower()),
        (1, word(7), "0xa9059cbb"),
        (2, word(7), "0x03e8"),
    ]


def test_map_in_nft_collection() -> None:
    descriptor = convert_one(
        "transferNft(uint256 tokenId, uint256 kind)",
        [{"path": "tokenId", "label": "NFT", "format": "nftName", "params": {"collection": map_ref("c", "kind")}}],
        {"c": {"1": TOKEN_A}},
    )

    param = descriptor.fields[0].param
    assert isinstance(param, CalldataDescriptorParamNFTV1)
    assert isinstance(param.collection, CalldataDescriptorValueMapRefV1)
    assert entries(descriptor) == [(0, word(1), TOKEN_A.lower())]


def test_descriptor_with_maps_round_trips() -> None:
    descriptor = convert_one(DEPOSIT, [token_amount("marketId")], {"tokens": {"1": TOKEN_A}})

    assert CalldataDescriptorV1.model_validate_json(descriptor.model_dump_json()) == descriptor


@pytest.mark.parametrize(
    ("signature", "field", "maps"),
    [
        pytest.param(DEPOSIT, token_amount("marketId"), {"tokens": {"one": TOKEN_A}}, id="key_not_an_integer"),
        pytest.param(DEPOSIT, token_amount("marketId"), {"tokens": {"-1": TOKEN_A}}, id="negative_unsigned_key"),
        pytest.param(
            "f(uint256 assets, uint8 k)", token_amount("k"), {"tokens": {"256": TOKEN_A}}, id="key_too_wide_for_type"
        ),
        pytest.param(
            DEPOSIT, token_amount("marketId"), {"tokens": {"1": TOKEN_A, "0x01": TOKEN_B}}, id="duplicate_key"
        ),
        pytest.param(DEPOSIT, token_amount("marketId"), {"tokens": {"1": "0x1234"}}, id="value_not_an_address"),
        pytest.param(
            "f(uint256 assets, string k)",
            token_amount("k"),
            {"tokens": {"x" * 33: TOKEN_A}},
            id="key_too_long_for_device",
        ),
        pytest.param(
            "f(uint256 assets, bytes k)", token_amount("k.[0:4]"), {"tokens": {"0x1234": TOKEN_A}}, id="key_not_slice"
        ),
        pytest.param(
            "f(uint256 assets, uint256[] ks)", token_amount("ks.[]"), {"tokens": {"1": TOKEN_A}}, id="key_is_array"
        ),
        pytest.param(
            "transfer(address to, uint256 key)",
            {
                "path": "to",
                "label": "To",
                "format": "addressName",
                "params": {"types": ["eoa"], "senderAddress": map_ref("tokens", "key")},
            },
            {"tokens": {"1": TOKEN_A}},
            id="sender_address_cannot_be_looked_up",
        ),
    ],
)
def test_invalid_map_lookups_are_rejected(signature: str, field: dict[str, Any], maps: dict[str, Any]) -> None:
    assert convert(signature, [field], maps) == []


def test_map_value_too_long_for_device_is_rejected() -> None:
    field = {
        "path": "data",
        "label": "Call",
        "format": "calldata",
        "params": {"calleePath": "target", "selector": map_ref("selectors", "route")},
    }
    assert (
        convert("execute(address target, uint256 route, bytes data)", [field], {"selectors": {"1": "0x" + "ab" * 33}})
        == []
    )


def test_single_array_element_key_is_supported() -> None:
    descriptor = convert_one("f(uint256 assets, uint256[] ks)", [token_amount("ks.[1]")], {"tokens": {"1": TOKEN_A}})

    assert entries(descriptor) == [(0, word(1), TOKEN_A.lower())]
