"""
V2 linter that validates the ``domainSeparator`` of an EIP-712 context against the domain of the descriptor.

The device is given the type of the domain reconstructed from the descriptor, so a ``domainSeparator`` has to be the
one of this domain: the calldata converter rejects a descriptor whose separator differs from the one computed from the
declared domain and deployments. This linter reports it, for instance when the signed domain has more members (such as
a ``version``) than the descriptor declares.
"""

from typing import final, override

from erc7730.common.binary import from_hex
from erc7730.common.output import ListOutputAdder, OutputAdder
from erc7730.convert.calldata.v1.eip712_schema import bind_domain, compute_domain_separator, reconstruct_domain_fields
from erc7730.lint.v2 import ERC7730Linter
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.v2.context import ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor


@final
class ValidateEIP712DomainSeparatorLinter(ERC7730Linter):
    """
    Validates that the ``domainSeparator`` of an EIP-712 context matches the separator computed from the domain.
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

        domain_fields = reconstruct_domain_fields(eip712.domain, bool(eip712.deployments))
        bindings = [bind_domain(eip712.domain, deployment, ListOutputAdder()) for deployment in eip712.deployments]
        if not eip712.deployments:
            bindings = [bind_domain(eip712.domain, None, ListOutputAdder())]

        computed = [
            compute_domain_separator(domain_fields, eip712.domain, binding, ListOutputAdder()) if binding else None
            for binding in bindings
        ]
        known = [separator for separator in computed if separator is not None]
        matching = [separator for separator in known if from_hex(separator) == declared_bytes]

        if not matching:
            out.error(
                title="Domain separator mismatch",
                message=f"Domain separator {declared} is not the one computed from the domain "
                f"({', '.join(sorted(known)) or 'it cannot be computed'}). Declare every member of the domain (name, "
                "version, chainId, verifyingContract, salt), otherwise the converter rejects the descriptor and the "
                "device cannot match its messages.",
            )
        elif len(matching) < len(computed):
            out.warning(
                title="Domain separator shared by several deployments",
                message=f"Domain separator {declared} matches only some of the {len(computed)} deployments, as it "
                "depends on the chain id and the verifying contract: the others are rejected by the converter. Omit it "
                "to compute one per deployment.",
            )
