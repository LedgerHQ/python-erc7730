"""
V2 linter that validates EIP-712 display format keys are syntactically valid ``encodeType`` strings.

In v2, EIP-712 descriptors do not embed the message schema anymore: the ``display.formats`` keys *are* the schema.
Per the ERC-7730 specification, an EIP-712 format key MUST be the string returned by the ``encodeType`` function
defined in EIP-712, applied to the primary type of the message, so that the type hash computed by the wallet from
the message matches the one computed from the descriptor key::

    keccak256(encodeType(typeOf(s))) == keccak256(TYPE_KEY)

Any deviation (stray whitespace, missing dependent type, wrong ordering, ...) yields a different hash, meaning the
descriptor would silently never apply. As the descriptor holds neither the domain nor the struct definitions, keys
can only be checked *syntactically* -- which is exactly what this linter does, purely locally.

Grammar validated here, from the EIP-712 specification (https://eips.ethereum.org/EIPS/eip-712)::

    encodeType  := structDef+
    structDef   := identifier "(" [ member ("," member)* ] ")"
    member      := type " " identifier
    type        := (atomicType | dynamicType | identifier) ("[" [ number ] "]")*

with the referenced struct types collected, sorted by name, and appended to the primary type encoding.
"""

import re
from typing import final, override

from erc7730.common.output import OutputAdder
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.resolved.v2.context import ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor

# a valid Solidity identifier, used for member names
_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"

# a struct type name: an identifier, optionally namespaced with colon separated segments. EIP-712 mandates a plain
# identifier, but colon namespacing is used in the wild (e.g. Hyperliquid's `HyperliquidTransaction:Withdraw`) and
# hashes fine, so it is tolerated here, consistently with `erc7730.common.abi.parse_encode_type`.
_TYPE_NAME = rf"{_IDENTIFIER}(?::{_IDENTIFIER})*"

# a type reference: a type name followed by any number of (fixed or dynamic) array suffixes
_TYPE = rf"{_TYPE_NAME}(?:\[[0-9]*\])*"

# the whole key: a concatenation of struct definitions, with nothing (not even whitespace) in between
_ENCODE_TYPE_PATTERN = re.compile(rf"(?:{_TYPE_NAME}\([^()]*\))+")

# a single struct definition, used to iterate over the key
_STRUCT_DEFINITION_PATTERN = re.compile(rf"({_TYPE_NAME})\(([^()]*)\)")

# a single struct member: exactly one space between the type and the member name
_MEMBER_PATTERN = re.compile(rf"({_TYPE}) ({_IDENTIFIER})")

# array suffixes, to strip from a type reference to get its base type
_ARRAY_SUFFIX_PATTERN = re.compile(r"(?:\[[0-9]*\])+$")

# types that look like Solidity value types but are not valid EIP-712 atomic types (aliases, out of range sizes,
# fixed point numbers), reported with a dedicated message rather than as an undefined struct type
_PRIMITIVE_LOOKALIKE_PATTERN = re.compile(r"byte|bytes[0-9]+|u?int[0-9]*|u?fixed(?:[0-9]+x[0-9]+)?")

# EIP-712 dynamic types, plus the atomic types that have no size suffix
_UNSIZED_TYPES = {"bool", "address", "string", "bytes"}


def _is_atomic_type(type_name: str) -> bool:
    """Whether a type name is an EIP-712 atomic or dynamic type.

    Note EIP-712 supports neither the ``uint``/``int``/``byte`` Solidity aliases nor fixed point numbers.

    :param type_name: the base type name, without array suffixes
    :return: True if the type is a valid EIP-712 atomic or dynamic type
    """
    if type_name in _UNSIZED_TYPES:
        return True
    if (match := re.fullmatch(r"bytes([1-9][0-9]?)", type_name)) is not None:
        return 1 <= int(match.group(1)) <= 32
    if (match := re.fullmatch(r"u?int([1-9][0-9]{0,2})", type_name)) is not None:
        return 8 <= (size := int(match.group(1))) <= 256 and size % 8 == 0
    return False


def _base_type(type_name: str) -> str:
    """Strip array suffixes from a type reference, e.g. ``Person[2][]`` -> ``Person``."""
    return _ARRAY_SUFFIX_PATTERN.sub("", type_name)


def validate_eip712_key(key: str, out: OutputAdder) -> None:
    """Validate an EIP-712 display format key is a syntactically valid ``encodeType`` string.

    Emits an error for each of:
    * a key that does not match the ``encodeType`` grammar (stray whitespace, unbalanced parenthesis, ...),
    * a struct or member name defined twice,
    * a member type that is neither a valid EIP-712 atomic type nor a struct defined in the key,
    * a struct defined in the key but never referenced,
    * dependent struct types not sorted by name.

    :param key: the ``display.formats`` key to validate
    :param out: output adder
    """
    if _ENCODE_TYPE_PATTERN.fullmatch(key) is None:
        return out.error(
            title="Invalid EIP-712 key",
            message=f'Display format key "{key}" is not a valid EIP-712 encodeType string: it must be a '
            f'concatenation of type definitions written as "TypeName(type1 name1,type2 name2)", with no '
            f"whitespace or other character in between.",
        )

    definitions: dict[str, list[tuple[str, str]]] = {}
    for definition in _STRUCT_DEFINITION_PATTERN.finditer(key):
        struct_name, members_string = definition.group(1), definition.group(2)

        if struct_name in definitions:
            out.error(
                title="Duplicate type in EIP-712 key",
                message=f'Type "{struct_name}" is defined more than once in display format key "{key}". Each '
                f"referenced type must be defined exactly once.",
            )
            continue

        members: list[tuple[str, str]] = []
        member_names: set[str] = set()
        for member_string in members_string.split(",") if members_string else []:
            if (member := _MEMBER_PATTERN.fullmatch(member_string)) is None:
                out.error(
                    title="Invalid EIP-712 key",
                    message=f'Member "{member_string}" of type "{struct_name}" in display format key "{key}" is '
                    f'not valid: members must be written as "type name", separated by a single space, with no '
                    f"other whitespace.",
                )
                continue
            member_type, member_name = member.group(1), member.group(2)
            if member_name in member_names:
                out.error(
                    title="Duplicate member in EIP-712 key",
                    message=f'Member "{member_name}" is defined more than once in type "{struct_name}" of display '
                    f'format key "{key}".',
                )
                continue
            member_names.add(member_name)
            members.append((member_type, member_name))

        definitions[struct_name] = members

    if not definitions:
        return None

    primary_type, *dependent_types = definitions

    _validate_member_types(key, definitions, out)
    _validate_dependent_types(key, primary_type, dependent_types, definitions, out)
    return None


def _validate_member_types(key: str, definitions: dict[str, list[tuple[str, str]]], out: OutputAdder) -> None:
    """Validate all member types are either EIP-712 atomic types or struct types defined in the key."""
    for struct_name, members in definitions.items():
        for member_type, member_name in members:
            if _is_atomic_type(base_type := _base_type(member_type)) or base_type in definitions:
                continue
            if _PRIMITIVE_LOOKALIKE_PATTERN.fullmatch(base_type) is not None:
                out.error(
                    title="Invalid type in EIP-712 key",
                    message=f'Member "{member_name}" of type "{struct_name}" in display format key "{key}" has type '
                    f'"{member_type}", which is not a valid EIP-712 atomic type. Valid atomic types are bytes1 to '
                    f"bytes32, uint8 to uint256, int8 to int256, bool, address, string and bytes (the uint, int and "
                    f"byte aliases and fixed point numbers are not supported).",
                )
            else:
                out.error(
                    title="Undefined type in EIP-712 key",
                    message=f'Member "{member_name}" of type "{struct_name}" in display format key "{key}" has type '
                    f'"{member_type}", which is not defined in the key. Referenced struct types must be appended to '
                    f"the primary type encoding.",
                )


def _validate_dependent_types(
    key: str,
    primary_type: str,
    dependent_types: list[str],
    definitions: dict[str, list[tuple[str, str]]],
    out: OutputAdder,
) -> None:
    """Validate dependent types are all referenced (transitively) from the primary type, and sorted by name."""
    referenced: set[str] = set()
    pending = [primary_type]
    while pending:
        if (struct_name := pending.pop()) in referenced:
            continue
        referenced.add(struct_name)
        pending.extend(
            base_type
            for member_type, _ in definitions.get(struct_name, [])
            if (base_type := _base_type(member_type)) in definitions
        )

    for struct_name in dependent_types:
        if struct_name not in referenced:
            out.error(
                title="Unused type in EIP-712 key",
                message=f'Type "{struct_name}" is defined in display format key "{key}" but is not referenced by '
                f'the primary type "{primary_type}". Only referenced struct types must be appended.',
            )

    if dependent_types != (expected := sorted(dependent_types)):
        out.error(
            title="Invalid type order in EIP-712 key",
            message=f'Types referenced by the primary type "{primary_type}" in display format key "{key}" must be '
            f"sorted by name. Found: ({', '.join(dependent_types)}), expected: ({', '.join(expected)}).",
        )


@final
class ValidateEIP712KeysLinter(ERC7730Linter):
    """
    Validates that EIP-712 display format keys are syntactically valid EIP-712 ``encodeType`` strings.

    Only applies to EIP-712 contexts: for contract contexts, format keys are function signatures or selectors.
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if not isinstance(descriptor.context, ResolvedEIP712Context):
            return
        for key in descriptor.display.formats:
            validate_eip712_key(key, out)
