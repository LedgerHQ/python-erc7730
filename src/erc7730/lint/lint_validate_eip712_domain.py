from typing import final, override

from eip712.model.schema import EIP712SchemaField

from erc7730.common.output import OutputAdder
from erc7730.lint import ERC7730Linter
from erc7730.model.resolved.context import EIP712Schema, ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor

# EIP-712 canonical domain field order and types as specified in the EIP-712 standard.
# See https://eips.ethereum.org/EIPS/eip-712#definition-of-domainseparator
EIP712_DOMAIN_CANONICAL_ORDER: list[tuple[str, str]] = [
    ("name", "string"),
    ("version", "string"),
    ("chainId", "uint256"),
    ("verifyingContract", "address"),
    ("salt", "bytes32"),
]

_EIP712_DOMAIN_KNOWN_NAMES = {name for name, _ in EIP712_DOMAIN_CANONICAL_ORDER}


def validate_eip712_domain_fields(
    domain_fields: list[EIP712SchemaField],
    out: OutputAdder,
) -> None:
    """Validate the EIP712Domain type fields against the canonical EIP-712 order.

    Emits:
    * Warning for fields not in the canonical list (name, version, chainId, verifyingContract, salt).
    * Error for fields that are out of the EIP-712 canonical order.

    :param domain_fields: the EIP712Domain fields from the schema
    :param out: warning handler
    """
    canonical_order = [name for name, _ in EIP712_DOMAIN_CANONICAL_ORDER]

    # Check for unknown fields
    for field in domain_fields:
        if field.name not in _EIP712_DOMAIN_KNOWN_NAMES:
            out.warning(
                title="Non-standard EIP712Domain field",
                message=f'EIP712Domain field "{field.name}" is not part of the EIP-712 standard '
                f"(expected: {', '.join(canonical_order)}).",  # no brackets — rich interprets them as tags
            )

    # Check ordering: filter to only known fields and verify they appear in canonical order
    known_field_names = [f.name for f in domain_fields if f.name in _EIP712_DOMAIN_KNOWN_NAMES]
    canonical_positions = {name: i for i, name in enumerate(canonical_order)}
    expected_order = sorted(known_field_names, key=lambda n: canonical_positions[n])

    if known_field_names != expected_order:
        out.error(
            title="EIP712Domain field order",
            message=f"EIP712Domain fields are not in the canonical EIP-712 order. "
            f"Found: ({', '.join(known_field_names)}), "
            f"expected: ({', '.join(expected_order)}).",
        )


@final
class ValidateEIP712DomainLinter(ERC7730Linter):
    """Validate ``EIP712Domain`` field ordering and names in EIP-712 schemas.

    For each schema that includes an ``EIP712Domain`` type, this linter checks that:
    * All fields are part of the canonical EIP-712 set (name, version, chainId, verifyingContract, salt).
    * Fields appear in the canonical EIP-712 order.
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if not isinstance(descriptor.context, ResolvedEIP712Context):
            return
        if descriptor.context.eip712.schemas is None:
            return
        for schema in descriptor.context.eip712.schemas:
            if isinstance(schema, EIP712Schema) and "EIP712Domain" in schema.types:
                validate_eip712_domain_fields(schema.types["EIP712Domain"], out)
