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

    @classmethod
    def _validate_contract_abis(cls, context: ResolvedContractContext, out: OutputAdder) -> None:
        if not isinstance(context.contract.abi, list):
            raise ValueError("Contract ABIs should have been resolved")

        if (deployments := context.contract.deployments) is None:
            return
        for deployment in deployments:
            skipped = "descriptor ABIs will not be validated"
            try:
                abis = client.get_contract_abis(deployment.chainId, deployment.address)
            except client.ProxyImplementationNotVerifiedError as e:
                out.warning(title="Proxy implementation not verified", message=f"{e}, {skipped}")
                continue
            except client.ContractNotVerifiedError as e:
                out.warning(title="Contract not verified", message=f"{e}, {skipped}")
                continue
            except client.ChainNotSupportedError as e:
                out.info(title="Chain not supported", message=f"{e}, {skipped}")
                continue
            except Exception as e:
                out.warning(
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
