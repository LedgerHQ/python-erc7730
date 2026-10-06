"""
V2 linter that validates the keys of maps looked up with a key read from the transaction.

The device reads the key from the transaction and matches it byte for byte against the map keys, so each map key must
be encodable as the value at the key path (for instance, a uint32 key must fit in 4 bytes).
"""

from typing import assert_never, final, override

from erc7730.common.output import OutputAdder
from erc7730.convert.calldata.v1.abi import ABITree, function_to_abi_tree
from erc7730.convert.calldata.v1.map import encode_map_keys
from erc7730.lint.v2 import ERC7730Linter
from erc7730.lint.v2.lint_validate_display_fields import parse_declared_abis
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.paths import ContainerField, ContainerPath
from erc7730.model.resolved.v2.context import ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from erc7730.model.resolved.v2.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedValueMap,
)


@final
class ValidateMapKeysLinter(ERC7730Linter):
    """
    Validates that the keys of maps looked up with a key read from the transaction can be encoded as the key value.

    Maps keyed on the chain id or the target contract address are resolved for each deployment and validated during
    resolution. Only contract descriptors with function signatures as format keys are validated: the ABI is needed to
    know how the key is encoded.
    """

    @override
    def lint(
        self, input_descriptor: InputERC7730Descriptor, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> None:
        match descriptor.context:
            case ResolvedEIP712Context():
                pass  # map lookups are not supported for EIP-712 messages by the device
            case ResolvedContractContext():
                abis = parse_declared_abis(input_descriptor)
                for selector, fmt in descriptor.display.formats.items():
                    if (abi := abis.get(selector)) is None:
                        continue
                    abi_tree = function_to_abi_tree(abi)
                    for field in fmt.fields:
                        _validate_field(field, abi_tree, out)
            case _:
                assert_never(descriptor.context)


def _validate_field(field: ResolvedField, abi_tree: ABITree, out: OutputAdder) -> None:
    match field:
        case ResolvedFieldDescription():
            if field.params is None:
                return
            for _, param in field.params:
                if isinstance(param, ResolvedValueMap) and not _is_deployment_key(param):
                    encode_map_keys(param, abi_tree, out)
        case ResolvedFieldGroup():
            for sub_field in field.fields:
                _validate_field(sub_field, abi_tree, out)
        case _:
            assert_never(field)


def _is_deployment_key(value_map: ResolvedValueMap) -> bool:
    """Whether the map key is provided by the deployment (chain id or target contract address)."""
    return isinstance(value_map.keyPath, ContainerPath) and value_map.keyPath.field in (
        ContainerField.CHAIN_ID,
        ContainerField.TO,
    )
