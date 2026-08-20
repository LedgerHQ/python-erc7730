import json
from typing import Any

from eth_utils import keccak

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.convert.calldata.v1.tlv import tlv_eip712_field, tlv_eip712_path_element
from erc7730.model.calldata.v1.descriptor import CalldataDescriptorEIP712V1
from erc7730.model.calldata.v1.eip712 import CalldataDescriptorEIP712FieldV1, CalldataDescriptorEIP712SolType
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorEIP712PathElementArraySliceV1,
    CalldataDescriptorEIP712PathElementStructFieldV1,
    CalldataDescriptorEIP712PathV1,
    CalldataDescriptorValuePathV1,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor

DEFAULT_CHAIN_ID = 1
DEFAULT_ADDRESS = "0x000000000000000000000000000000000000dEaD"


def _eip712_path(descriptor: CalldataDescriptorEIP712V1, index: int) -> CalldataDescriptorEIP712PathV1:
    """Return the EIP-712 binary path of the given field, asserting its type."""
    value = descriptor.fields[index].param.value
    assert isinstance(value, CalldataDescriptorValuePathV1)
    path = value.binary_path
    assert isinstance(path, CalldataDescriptorEIP712PathV1)
    return path


def _convert(
    encode_type: str,
    fields: list[dict[str, Any]],
    *,
    domain: dict[str, Any] | None = None,
    chain_id: int = DEFAULT_CHAIN_ID,
) -> CalldataDescriptorEIP712V1:
    """Build a minimal EIP-712 v2 descriptor and return the single converted calldata descriptor."""
    descriptor = InputERC7730Descriptor.model_validate_json(
        json.dumps(
            {
                "$schema": "specs/erc7730-v2.schema.json",
                "context": {
                    "$id": "test",
                    "eip712": {
                        "deployments": [{"chainId": chain_id, "address": DEFAULT_ADDRESS}],
                        "domain": domain if domain is not None else {"name": "Test", "version": "1"},
                    },
                },
                "metadata": {"owner": "Test Owner"},
                "display": {"formats": {encode_type: {"intent": "Test intent", "fields": fields}}},
            }
        )
    )

    descriptors = erc7730_v2_descriptor_to_calldata_descriptors(descriptor, chain_id=chain_id)
    assert len(descriptors) == 1
    descriptor_out = descriptors[0]
    assert isinstance(descriptor_out, CalldataDescriptorEIP712V1)
    return descriptor_out


PERMIT_TYPE = "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"


def test_eip712_binding_and_primary_type_hash() -> None:
    descriptor = _convert(
        PERMIT_TYPE,
        [{"path": "value", "label": "Value", "format": "amount"}],
    )

    assert descriptor.type == "eip712"
    assert descriptor.version == "v1"
    assert descriptor.primary_type_hash == "0x" + keccak(text=PERMIT_TYPE).hex()
    assert descriptor.message_info.primary_type_hash == descriptor.primary_type_hash


def test_eip712_schema_reconstruction_includes_domain_and_message_types() -> None:
    descriptor = _convert(
        PERMIT_TYPE,
        [{"path": "value", "label": "Value", "format": "amount"}],
        domain={"name": "Test", "version": "1"},
    )

    structs = {struct.name: struct for struct in descriptor.schema_info.structs}
    assert set(structs) == {"EIP712Domain", "Permit"}

    # domain: name, version present; deployments imply chainId + verifyingContract
    domain_fields = [(f.name, f.sol_type) for f in structs["EIP712Domain"].fields]
    assert domain_fields == [
        ("name", CalldataDescriptorEIP712SolType.STRING),
        ("version", CalldataDescriptorEIP712SolType.STRING),
        ("chainId", CalldataDescriptorEIP712SolType.UINT),
        ("verifyingContract", CalldataDescriptorEIP712SolType.ADDRESS),
    ]

    permit_fields = [(f.name, f.sol_type) for f in structs["Permit"].fields]
    assert permit_fields == [
        ("owner", CalldataDescriptorEIP712SolType.ADDRESS),
        ("spender", CalldataDescriptorEIP712SolType.ADDRESS),
        ("value", CalldataDescriptorEIP712SolType.UINT),
        ("nonce", CalldataDescriptorEIP712SolType.UINT),
        ("deadline", CalldataDescriptorEIP712SolType.UINT),
    ]


def test_eip712_field_path_uses_struct_field_indices() -> None:
    descriptor = _convert(
        PERMIT_TYPE,
        [
            {"path": "owner", "label": "Owner", "format": "addressName", "params": {"types": ["wallet"]}},
            {"path": "value", "label": "Value", "format": "amount"},
            {"path": "deadline", "label": "Deadline", "format": "date", "params": {"encoding": "timestamp"}},
        ],
    )

    assert len(descriptor.fields) == 3

    # owner -> field 0, value -> field 2, deadline -> field 4 of Permit
    assert _eip712_path(descriptor, 0).elements == [CalldataDescriptorEIP712PathElementStructFieldV1(index=0)]
    assert _eip712_path(descriptor, 1).elements == [CalldataDescriptorEIP712PathElementStructFieldV1(index=2)]
    assert _eip712_path(descriptor, 2).elements == [CalldataDescriptorEIP712PathElementStructFieldV1(index=4)]


def test_eip712_nested_struct_and_array_path() -> None:
    descriptor = _convert(
        "Batch(Transfer[] transfers)Transfer(address to,uint256 amount)",
        [
            {"path": "transfers.[].to", "label": "To", "format": "addressName", "params": {"types": ["wallet"]}},
            {"path": "transfers.[].amount", "label": "Amount", "format": "amount"},
        ],
    )

    structs = {struct.name: struct for struct in descriptor.schema_info.structs}
    assert set(structs) == {"EIP712Domain", "Batch", "Transfer"}

    # transfers is a dynamic array of Transfer structs
    transfers_field = structs["Batch"].fields[0]
    assert transfers_field.sol_type == CalldataDescriptorEIP712SolType.STRUCT
    assert transfers_field.struct_name == "Transfer"
    assert transfers_field.array_dimensions == [None]

    to_path = _eip712_path(descriptor, 0)
    assert to_path.elements == [
        CalldataDescriptorEIP712PathElementStructFieldV1(index=0),  # transfers
        CalldataDescriptorEIP712PathElementArraySliceV1(),  # wildcard over array
        CalldataDescriptorEIP712PathElementStructFieldV1(index=0),  # to
    ]

    amount_path = _eip712_path(descriptor, 1)
    assert amount_path.elements == [
        CalldataDescriptorEIP712PathElementStructFieldV1(index=0),  # transfers
        CalldataDescriptorEIP712PathElementArraySliceV1(),  # wildcard over array
        CalldataDescriptorEIP712PathElementStructFieldV1(index=1),  # amount
    ]


def test_eip712_descriptor_serializes_to_tlv_and_json() -> None:
    descriptor = _convert(
        PERMIT_TYPE,
        [{"path": "value", "label": "Value", "format": "amount"}],
    )

    # computed TLV descriptor fields must be non-empty hex
    assert bytes.fromhex(descriptor.message_info.descriptor)
    assert bytes.fromhex(descriptor.schema_info.descriptor)
    for field in descriptor.fields:
        assert bytes.fromhex(field.descriptor)

    assert descriptor.model_dump_json()


def _uint_field(dimensions: list[int | None]) -> CalldataDescriptorEIP712FieldV1:
    return CalldataDescriptorEIP712FieldV1(
        name="x", sol_type=CalldataDescriptorEIP712SolType.UINT, type_size=1, array_dimensions=dimensions
    )


def test_eip712_array_dim_tlv_matches_spec_examples() -> None:
    # ARRAY_DIM encoding, per the app-ethereum spec: T[2] -> 040102, T[0] -> 040100, T[] -> 0400
    assert tlv_eip712_field(_uint_field([2])).hex().endswith("040102")
    assert tlv_eip712_field(_uint_field([0])).hex().endswith("040100")
    assert tlv_eip712_field(_uint_field([None])).hex().endswith("0400")


def test_eip712_path_element_tlv_encoding() -> None:
    # EIP712_STRUCT_FIELD: tag 0x01, uint8 index
    assert tlv_eip712_path_element(CalldataDescriptorEIP712PathElementStructFieldV1(index=1)).hex() == "010101"

    # EIP712_ARRAY_SLICE: tag 0x02 wrapping START (0x01) / END (0x02), each a fixed-width 2-byte signed int
    assert (
        tlv_eip712_path_element(CalldataDescriptorEIP712PathElementArraySliceV1(start=2, end=3)).hex()
        == "02080102000202020003"
    )

    # negative index sign-extends across the full 2 bytes (0xffff), not minimal length
    assert tlv_eip712_path_element(CalldataDescriptorEIP712PathElementArraySliceV1(start=-1)).hex() == "02040102ffff"

    # wildcard slice (no START/END) is an empty payload
    assert tlv_eip712_path_element(CalldataDescriptorEIP712PathElementArraySliceV1()).hex() == "0200"
