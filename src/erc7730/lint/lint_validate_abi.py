from typing import final, override

from erc7730.common import client
from erc7730.common.abi import compute_signature, get_functions
from erc7730.common.output import OutputAdder
from erc7730.lint import ERC7730Linter
from erc7730.model.resolved.context import ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor


@final
class ValidateABILinter(ERC7730Linter):
    """
    - resolves the ABI from the descriptor (URL or provided)
    - resolves the ABI from *scan (given chainId and address of descriptor)
    - => compares the two ABIs
    """

    def __init__(self, require_verified: bool = False) -> None:
        """
        :param require_verified: report a contract that is not verified on Sourcify as an error instead of a warning
            (as well as a reference ABI that could not be fetched, for instance because of a rate limit)
        """
        self.require_verified = require_verified

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if isinstance(descriptor.context, ResolvedEIP712Context):
            return self._validate_eip712_schemas(descriptor.context, out)
        if isinstance(descriptor.context, ResolvedContractContext):
            return self._validate_contract_abis(descriptor.context, out)
        raise ValueError("Invalid context type")

    @classmethod
    def _validate_eip712_schemas(cls, context: ResolvedEIP712Context, out: OutputAdder) -> None:
        pass  # not implemented

    def _validate_contract_abis(self, context: ResolvedContractContext, out: OutputAdder) -> None:
        if not isinstance(context.contract.abi, list):
            raise ValueError("Contract ABIs should have been resolved")

        if (deployments := context.contract.deployments) is None:
            return
        for deployment in deployments:
            skipped = "descriptor ABIs will not be validated"
            unverified = out.error if self.require_verified else out.warning
            unsupported = out.error if self.require_verified else out.info
            failed = out.error if self.require_verified else out.warning
            try:
                abis = client.get_contract_abis(deployment.chainId, deployment.address)
            except client.ProxyImplementationNotVerifiedError as e:
                unverified(title="Proxy implementation not verified", message=f"{e}, {skipped}")
                continue
            except client.ContractNotVerifiedError as e:
                unverified(title="Contract not verified", message=f"{e}, {skipped}")
                continue
            except client.ChainNotSupportedError as e:
                unsupported(title="Chain not supported", message=f"{e}, {skipped}")
                continue
            except Exception as e:
                failed(
                    title="Could not fetch ABI",
                    message=f"Fetching reference ABI for chain id {deployment.chainId} failed, {skipped}: {e}",
                )
                continue

            reference_abis = get_functions(abis)
            descriptor_abis = get_functions(context.contract.abi)
            url = client.get_contract_explorer_url(deployment.chainId, deployment.address)

            for selector, abi in descriptor_abis.functions.items():
                if selector not in reference_abis.functions:
                    out.warning(
                        title="Extra function",
                        message=f"Function {compute_signature(abi)} (selector: {selector}) defined in descriptor ABIs "
                        f"does not exist in reference ABI (see {url})",
                    )
                elif descriptor_abis.functions[selector] != reference_abis.functions[selector]:
                    out.warning(
                        title="Function mismatch",
                        message=f"Function {compute_signature(abi)} (selector: {selector}) defined in descriptor ABIs "
                        f"does not match reference ABI (see {url})",
                    )
