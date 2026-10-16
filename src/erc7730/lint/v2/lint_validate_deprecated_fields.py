"""
V2 linter that rejects the deprecated ``contract.abi`` and ``eip712.schemas`` context fields.

The ERC-7730 specification deprecates both fields: in v2, the ``display.formats`` keys declare the function
signatures and the EIP-712 ``encodeType`` strings. Resolution drops both fields, so this check reads the input
descriptor.
"""

from typing import final, override

from erc7730.common.output import OutputAdder
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.input.v2.context import InputContractContext, InputEIP712Context
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor

DEPRECATED_ABI_TITLE = "Deprecated ABI field"
DEPRECATED_SCHEMAS_TITLE = "Deprecated schemas field"


def validate_deprecated_fields(input_descriptor: InputERC7730Descriptor, out: OutputAdder) -> None:
    """Report an error for each deprecated context field set on the descriptor.

    :param input_descriptor: the input descriptor, as loaded from the file
    :param out: output adder
    """
    match input_descriptor.context:
        case InputContractContext(contract=contract) if contract.abi is not None:
            out.error(
                title=DEPRECATED_ABI_TITLE,
                message="The `context.contract.abi` field is deprecated and must not be set in v2 descriptors. "
                "Remove it: function signatures are declared by the `display.formats` keys, and ABIs are "
                "resolved from the verified contract.",
            )
        case InputEIP712Context(eip712=eip712) if eip712.schemas is not None:
            out.error(
                title=DEPRECATED_SCHEMAS_TITLE,
                message="The `context.eip712.schemas` field is deprecated and must not be set in v2 descriptors. "
                "Remove it: message types are declared by the `display.formats` keys, which must be EIP-712 "
                "`encodeType` strings.",
            )
        case _:
            pass


@final
class ValidateDeprecatedFieldsLinter(ERC7730Linter):
    """Rejects the deprecated ``contract.abi`` and ``eip712.schemas`` context fields."""

    @override
    def lint(
        self, input_descriptor: InputERC7730Descriptor, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> None:
        validate_deprecated_fields(input_descriptor, out)
