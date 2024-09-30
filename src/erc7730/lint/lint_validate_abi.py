from typing import final, override

from erc7730.common.abi import compute_signature, get_functions
from erc7730.common.client.etherscan import get_contract_abis
from erc7730.lint import ERC7730Linter
from erc7730.model.context import ContractContext, EIP712Context
from erc7730.model.descriptor import ERC7730Descriptor


@final
class ValidateABILinter(ERC7730Linter):
    """
    - resolves the ABI from the descriptor (URL or provided)
    - resolves the ABI from *scan (given chainId and address of descriptor)
    - => compares the two ABIs
    """

    @override
    def lint(self, descriptor: ERC7730Descriptor, out: ERC7730Linter.OutputAdder) -> None:
        if isinstance(descriptor.context, EIP712Context):
            return self._validate_eip712_schemas(descriptor.context, out)
        if isinstance(descriptor.context, ContractContext):
            return self._validate_contract_abis(descriptor.context, out)
        raise ValueError("Invalid context type")

    @classmethod
    def _validate_eip712_schemas(cls, context: EIP712Context, out: ERC7730Linter.OutputAdder) -> None:
        pass  # not implemented

    @classmethod
    def _validate_contract_abis(cls, context: ContractContext, out: ERC7730Linter.OutputAdder) -> None:
        if not isinstance(context.contract.abi, list):
            raise ValueError("Contract ABIs should have been resolved")

        if (deployments := context.contract.deployments) is None:
            return
        for deployment in deployments.root:
            if (chain_id := deployment.chainId) is None or (address := deployment.address) is None:
                continue

            if (abis := get_contract_abis(chain_id, address)) is None:
                continue

            reference_abis = get_functions(abis)
            descriptor_abis = get_functions(context.contract.abi)

            if reference_abis.proxy:
                out(
                    ERC7730Linter.Output(
                        title="Proxy contract",
                        message="Contract ABI on Etherscan is likely to be a proxy, validation skipped",
                        level=ERC7730Linter.Output.Level.INFO,
                    )
                )
                return

            for selector, abi in descriptor_abis.functions.items():
                if selector not in reference_abis.functions:
                    out(
                        ERC7730Linter.Output(
                            title="Missing function",
                            message=f"Function `{selector}/{compute_signature(abi)}` is not defined in Etherscan ABI",
                            level=ERC7730Linter.Output.Level.ERROR,
                        )
                    )
                else:
                    if descriptor_abis.functions[selector] != reference_abis.functions[selector]:
                        out(
                            ERC7730Linter.Output(
                                title="Function mismatch",
                                message=f"Function `{selector}/{compute_signature(abi)}` does not match Etherscan ABI",
                                level=ERC7730Linter.Output.Level.WARNING,
                            )
                        )