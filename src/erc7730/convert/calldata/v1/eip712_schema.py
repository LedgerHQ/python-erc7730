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
from erc7730.common.binary import from_hex
from erc7730.common.output import OutputAdder
from erc7730.model.calldata.v1.eip712 import (
    CalldataDescriptorEIP712FieldV1,
    CalldataDescriptorEIP712SolType,
    CalldataDescriptorEIP712StructV1,
)
from erc7730.model.resolved.v2.context import ResolvedDeployment, ResolvedDomain
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


@dataclass(frozen=True)
class EIP712DomainBinding:
    """Chain id and verifying contract of the domain of the messages, either of which may be unknown."""

    chain_id: int | None
    address: str | None


def bind_domain(
    domain: ResolvedDomain | None, deployment: ResolvedDeployment | None, out: OutputAdder
) -> EIP712DomainBinding | None:
    """
    Resolve the chain id and verifying contract of the domain of the messages of a deployment.

    The deployment provides them when the domain does not declare them, which is also the only source for a descriptor
    without deployment. A domain declaring a chain id or a verifying contract the deployment is not on is rejected,
    as no message of the deployment can have this domain.

    :param domain: the resolved EIP-712 domain
    :param deployment: the deployment the descriptor is generated for, if any
    :param out: error handler
    :return: the binding, or None on error
    """
    domain_chain_id = domain.chainId if domain is not None else None
    domain_address = domain.verifyingContract if domain is not None else None
    if deployment is None:
        return EIP712DomainBinding(chain_id=domain_chain_id, address=domain_address)

    if domain_chain_id is not None and domain_chain_id != deployment.chainId:
        return out.error(
            title="Conflicting domain chain id",
            message=f"The domain chain id {domain_chain_id} is not the one of the deployment {deployment.chainId}.",
        )
    if domain_address is not None and domain_address.lower() != deployment.address.lower():
        return out.error(
            title="Conflicting domain verifying contract",
            message=f"The domain verifying contract {domain_address} is not the one of the deployment "
            f"{deployment.address}.",
        )
    return EIP712DomainBinding(chain_id=deployment.chainId, address=deployment.address)


def _integer_size(base: str, width: str) -> int:
    """Size in bytes of an integer type, which has to be written in its canonical form (``uint256`` not ``uint``)."""
    if not width or int(width) % 8 != 0 or not 8 <= int(width) <= 256 or width != str(int(width)):
        raise ValueError(f"{base} is not a valid type, an integer is written with its width, 8 to 256 by steps of 8")
    return int(width) // 8


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
        type_size = _integer_size(base, match.group(1))
    elif (match := re.fullmatch(r"int(\d*)", base)) is not None:
        sol_type = CalldataDescriptorEIP712SolType.INT
        type_size = _integer_size(base, match.group(1))
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
        if not 1 <= type_size <= 32:
            raise ValueError(f"{base} is not a valid type, bytesN is 1 to 32 bytes")
    else:
        # TODO fixed/ufixed Solidity types are not handled (rare in EIP-712); anything else is treated as a struct
        sol_type = CalldataDescriptorEIP712SolType.STRUCT
        struct_name = base

    return ParsedSolidityType(
        sol_type=sol_type, type_size=type_size, array_dimensions=dimensions, struct_name=struct_name
    )


def reconstruct_domain_fields(domain: ResolvedDomain | None, has_deployments: bool) -> list[tuple[str, str]]:
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

    domain_fields = reconstruct_domain_fields(domain, has_deployments)

    # the domain is described by the descriptor: a message type of the same name is the same type or a conflict
    if raw_types.get("EIP712Domain", domain_fields) != domain_fields:
        return out.error(
            title="Conflicting EIP712Domain",
            message=f"Format key '{encode_type_key}' defines EIP712Domain differently from the domain of the "
            "descriptor.",
        )

    types: dict[str, list[tuple[str, str]]] = {"EIP712Domain": domain_fields, **raw_types}
    structs: list[CalldataDescriptorEIP712StructV1] = []

    # a type outside the limits of the device is reported for this format only
    try:
        structs.extend(_build_struct(type_name, type_fields) for type_name, type_fields in types.items())
        for type_name, type_fields in types.items():
            for type_str, field_name in type_fields:
                if (struct_name := parse_solidity_type(type_str).struct_name) is not None and struct_name not in types:
                    raise ValueError(f"{type_name}.{field_name} refers to the undefined struct {struct_name}")
    except ValueError as e:
        return out.error(
            title="Unsupported EIP-712 type",
            message=f"Format key '{encode_type_key}' has a type the device cannot handle: {e}",
        )

    # PRIMARY_TYPE_HASH = keccak256(encodeType(primaryType)); normalize to canonical order so the hash does not
    # depend on the ordering of the source format key
    primary_type_hash = HexStr("0x" + keccak(text=to_encode_type(primary_type, raw_types)).hex())

    return ReconstructedSchema(
        primary_type=primary_type,
        primary_type_hash=primary_type_hash,
        types=types,
        structs=structs,
    )


def compute_domain_separator(
    domain_fields: list[tuple[str, str]],
    domain: ResolvedDomain | None,
    binding: EIP712DomainBinding,
    out: OutputAdder,
) -> HexStr | None:
    """
    Compute the domain separator, ``hashStruct(domain)``, of the messages of one deployment.

    :param domain_fields: the fields of the type of the domain (see ``reconstruct_domain_fields``)
    :param domain: the resolved EIP-712 domain, which holds the values of its name, version and salt
    :param binding: chain id and verifying contract of the domain
    :param out: error handler
    :return: the domain separator, or None on error
    """
    domain_type = f"EIP712Domain({','.join(f'{type_str} {name}' for type_str, name in domain_fields)})"

    encoded = bytearray(keccak(text=domain_type))
    for _, name in domain_fields:
        match name:
            case "name" | "version":
                value = getattr(domain, name)
                encoded += keccak(text=value)
            case "chainId":
                if binding.chain_id is None:
                    _missing_domain_value(name, out)
                    return None
                encoded += binding.chain_id.to_bytes(32)
            case "verifyingContract":
                if binding.address is None:
                    _missing_domain_value(name, out)
                    return None
                encoded += from_hex(binding.address).rjust(32, b"\x00")
            case "salt":
                salt_hex = domain.salt if domain is not None else None
                try:
                    salt = from_hex(salt_hex) if salt_hex is not None else b""
                except ValueError:
                    salt = b""
                if len(salt) != 32:
                    return out.error(
                        title="Invalid domain salt",
                        message=f"Domain salt {salt_hex} must be a 32 bytes hexadecimal string.",
                    )
                encoded += salt
            case _:
                raise ValueError(f"Unexpected domain field {name}")

    return HexStr("0x" + keccak(bytes(encoded)).hex())


def _missing_domain_value(name: str, out: OutputAdder) -> None:
    out.error(
        title="Missing domain value",
        message=f"Domain field {name} has no value: declare a deployment, or set it in the domain.",
    )
