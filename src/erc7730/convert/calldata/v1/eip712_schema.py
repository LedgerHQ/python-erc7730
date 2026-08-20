"""
Reconstruction of EIP-712 schema (EIP712_SCHEMA struct) from ERC-7730 v2 ``display.formats`` keys.

In ERC-7730 v2, the ``display.formats`` keys are EIP-712 ``encodeType`` strings (e.g.
``Order(address owner,Bridge bridge)Bridge(bytes4 sel,uint256 chainId)``) from which the whole schema can be
rebuilt. The ``EIP712Domain`` type is reconstructed separately from the descriptor domain / deployment information.

Referred to as "EIP712 v2" in the Ethereum app specifications (https://github.com/LedgerHQ/app-ethereum).
"""

import re
from dataclasses import dataclass, field

from eth_utils import keccak

from erc7730.common.abi import parse_encode_type, to_encode_type
from erc7730.common.output import OutputAdder
from erc7730.model.calldata.v1.eip712 import (
    CalldataDescriptorEIP712FieldV1,
    CalldataDescriptorEIP712SolType,
    CalldataDescriptorEIP712StructV1,
)
from erc7730.model.resolved.v2.context import ResolvedDomain
from erc7730.model.types import HexStr


@dataclass(frozen=True)
class ParsedSolidityType:
    """A Solidity type parsed into its base type, size and array dimensions."""

    sol_type: CalldataDescriptorEIP712SolType
    type_size: int | None
    array_dimensions: list[int | None]  # innermost first, None = dynamic dimension
    struct_name: str | None


@dataclass(frozen=True)
class ReconstructedSchema:
    """A reconstructed EIP-712 schema for a single message primary type."""

    primary_type: str
    primary_type_hash: HexStr
    # struct name -> ordered list of (type string, field name), including EIP712Domain
    types: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    structs: list[CalldataDescriptorEIP712StructV1] = field(default_factory=list)


def parse_solidity_type(type_str: str) -> ParsedSolidityType:
    """
    Parse a Solidity type string into base type, size and array dimensions.

    :param type_str: a Solidity type (e.g. ``uint256``, ``bytes32``, ``address[3][]``, ``Person``)
    :return: the parsed type
    """
    base = type_str
    dimensions: list[int | None] = []
    while base.endswith("]"):
        open_index = base.rfind("[")
        inner = base[open_index + 1 : -1]
        dimensions.append(int(inner) if inner else None)
        base = base[:open_index]
    # collected outermost first, but the spec wants innermost first
    dimensions.reverse()

    sol_type: CalldataDescriptorEIP712SolType
    type_size: int | None = None
    struct_name: str | None = None

    if (match := re.fullmatch(r"uint(\d*)", base)) is not None:
        sol_type = CalldataDescriptorEIP712SolType.UINT
        type_size = (int(match.group(1)) if match.group(1) else 256) // 8
    elif (match := re.fullmatch(r"int(\d*)", base)) is not None:
        sol_type = CalldataDescriptorEIP712SolType.INT
        type_size = (int(match.group(1)) if match.group(1) else 256) // 8
    elif base == "address":
        sol_type = CalldataDescriptorEIP712SolType.ADDRESS
    elif base == "bool":
        sol_type = CalldataDescriptorEIP712SolType.BOOL
    elif base == "string":
        sol_type = CalldataDescriptorEIP712SolType.STRING
    elif base == "bytes":
        sol_type = CalldataDescriptorEIP712SolType.BYTES_DYN
    elif (match := re.fullmatch(r"bytes(\d+)", base)) is not None:
        sol_type = CalldataDescriptorEIP712SolType.BYTES_FIX
        type_size = int(match.group(1))
    else:
        # TODO fixed/ufixed Solidity types are not handled (rare in EIP-712); anything else is treated as a struct
        sol_type = CalldataDescriptorEIP712SolType.STRUCT
        struct_name = base

    return ParsedSolidityType(
        sol_type=sol_type, type_size=type_size, array_dimensions=dimensions, struct_name=struct_name
    )


def _reconstruct_domain_fields(domain: ResolvedDomain | None, has_deployments: bool) -> list[tuple[str, str]]:
    """
    Reconstruct the ``EIP712Domain`` type fields, in canonical EIP-712 order.

    :param domain: the resolved domain, or None
    :param has_deployments: whether the descriptor declares deployments (implying chainId + verifyingContract)
    :return: ordered list of (type string, field name)
    """
    # append order is load-bearing: it must follow the canonical EIP-712 domain field order
    # (name, version, chainId, verifyingContract, salt), as it determines the reconstructed EIP712Domain type hash.
    fields: list[tuple[str, str]] = []
    if domain is not None and domain.name is not None:
        fields.append(("string", "name"))
    if domain is not None and domain.version is not None:
        fields.append(("string", "version"))
    # chainId / verifyingContract belong to the domain type when the domain declares them explicitly; when it omits
    # them but deployments are declared, they are still part of the signed domain (implied by the deployment).
    if (domain is not None and domain.chainId is not None) or has_deployments:
        fields.append(("uint256", "chainId"))
    if (domain is not None and domain.verifyingContract is not None) or has_deployments:
        fields.append(("address", "verifyingContract"))
    if domain is not None and domain.salt is not None:
        fields.append(("bytes32", "salt"))
    return fields


def _build_struct(name: str, type_fields: list[tuple[str, str]]) -> CalldataDescriptorEIP712StructV1:
    """Build an EIP712_STRUCT descriptor from a struct name and its (type, name) fields."""
    fields: list[CalldataDescriptorEIP712FieldV1] = []
    for type_str, field_name in type_fields:
        parsed = parse_solidity_type(type_str)
        fields.append(
            CalldataDescriptorEIP712FieldV1(
                name=field_name,
                sol_type=parsed.sol_type,
                type_size=parsed.type_size,
                array_dimensions=parsed.array_dimensions,
                struct_name=parsed.struct_name,
            )
        )
    return CalldataDescriptorEIP712StructV1(name=name, fields=fields)


def reconstruct_schema(
    encode_type_key: str,
    domain: ResolvedDomain | None,
    has_deployments: bool,
    out: OutputAdder,
) -> ReconstructedSchema | None:
    """
    Reconstruct an EIP-712 schema from an ``encodeType`` format key and the descriptor domain / deployment info.

    :param encode_type_key: an ``encodeType`` string from ``display.formats``
    :param domain: the resolved EIP-712 domain
    :param has_deployments: whether the descriptor declares deployments
    :param out: error handler
    :return: the reconstructed schema, or None on error
    """
    if encode_type_key.startswith("0x"):
        return out.error(
            title="Unsupported format key",
            message=f"Format key '{encode_type_key}' is already a hash, cannot reconstruct EIP-712 schema.",
        )

    try:
        primary_type, raw_types = parse_encode_type(encode_type_key)
    except ValueError as e:
        return out.error(
            title="Invalid encodeType",
            message=f"Failed to parse format key as encodeType: {e}",
        )

    types: dict[str, list[tuple[str, str]]] = {}
    structs: list[CalldataDescriptorEIP712StructV1] = []

    domain_fields = _reconstruct_domain_fields(domain, has_deployments)
    types["EIP712Domain"] = domain_fields
    structs.append(_build_struct("EIP712Domain", domain_fields))

    for type_name, type_fields in raw_types.items():
        types[type_name] = type_fields
        structs.append(_build_struct(type_name, type_fields))

    # PRIMARY_TYPE_HASH = keccak256(encodeType(primaryType)); normalize to canonical order so the hash does not
    # depend on the ordering of the source format key
    primary_type_hash = HexStr("0x" + keccak(text=to_encode_type(primary_type, raw_types)).hex())

    return ReconstructedSchema(
        primary_type=primary_type,
        primary_type_hash=primary_type_hash,
        types=types,
        structs=structs,
    )
