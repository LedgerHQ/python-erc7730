"""
V2 linter that validates the ``domainSeparator`` of an EIP-712 context against the domain of the descriptor.

The converter uses a ``domainSeparator`` given by the descriptor as is, as the ``domain`` constraint of a descriptor may
be only partial (the signed domain can have more members than the ones listed). This linter recomputes the separator
from the declared domain and deployments, and reports when none of them gives the declared value: the device would
never match the messages with it.
"""

from typing import final, override

from erc7730.common.binary import from_hex
from erc7730.common.output import ListOutputAdder, OutputAdder
from erc7730.convert.calldata.v1.eip712_schema import compute_domain_separator, reconstruct_schema
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.v2.context import ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor


@final
class ValidateEIP712DomainSeparatorLinter(ERC7730Linter):
    """
    Validates that the ``domainSeparator`` of an EIP-712 context matches the separator computed from the domain.

    Nothing is reported when the separator cannot be computed (no domain member, or a missing chain id / verifying
    contract), as there is nothing to compare it to.
    """

    @override
    def lint(
        self, input_descriptor: InputERC7730Descriptor, descriptor: ResolvedERC7730Descriptor, out: OutputAdder
    ) -> None:
        if not isinstance(descriptor.context, ResolvedEIP712Context):
            return

        eip712 = descriptor.context.eip712
        if not (declared := eip712.domainSeparator):
            return

        try:
            declared_bytes = from_hex(declared)
        except ValueError:
            declared_bytes = b""
        if len(declared_bytes) != 32:
            out.error(
                title="Invalid domain separator",
                message=f"Domain separator {declared} must be a 32 bytes hexadecimal string.",
            )
            return

        # the type of the domain does not depend on the format key: any valid one gives it
        schema = None
        for key in descriptor.display.formats:
            if schema := reconstruct_schema(str(key), eip712.domain, bool(eip712.deployments), ListOutputAdder()):
                break
        if schema is None or not schema.types["EIP712Domain"]:
            return

        # without deployment the chain id and verifying contract can only come from the domain
        bindings: list[tuple[int | None, str | None]] = [(d.chainId, d.address) for d in eip712.deployments]
        if not bindings:
            domain = eip712.domain
            bindings = [(domain.chainId, domain.verifyingContract) if domain else (None, None)]

        computed = [
            compute_domain_separator(schema, eip712.domain, chain_id, address, ListOutputAdder())
            for chain_id, address in bindings
        ]
        known = [separator for separator in computed if separator is not None]
        if not known:
            return

        expected = {bytes.fromhex(separator[2:]) for separator in known}
        if declared_bytes not in expected:
            out.warning(
                title="Domain separator mismatch",
                message=f"Domain separator {declared} is not the one computed from the domain "
                f"({', '.join(sorted(known))}). If the domain is partial this is expected, otherwise the device will "
                "not match the messages of this descriptor.",
            )
        elif len(known) > 1:
            out.warning(
                title="Domain separator shared by several deployments",
                message=f"Domain separator {declared} matches only some of the {len(known)} deployments, as it "
                "depends on the chain id and the verifying contract. Omit it to compute one per deployment.",
            )
