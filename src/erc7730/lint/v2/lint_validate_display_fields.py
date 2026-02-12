"""
V2 linter that validates display fields against reference ABIs fetched from Etherscan.

In v2, ABI and EIP-712 schemas are NOT embedded in the descriptor. Instead:
  - For contract context: fetch ABI from Etherscan, validate display field paths match ABI params,
    and check selector exhaustiveness.
  - For EIP-712 context: no schema to validate against (no-op).
"""

from typing import final, override

from erc7730.common import client
from erc7730.common.abi import compute_signature, get_functions
from erc7730.common.output import OutputAdder
from erc7730.lint.v2 import ERC7730Linter
from erc7730.lint.v2.path_schemas import compute_format_schema_paths
from erc7730.model.paths import DataPath
from erc7730.model.paths.path_schemas import compute_abi_schema_paths
from erc7730.model.resolved.v2.context import ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor


@final
class ValidateDisplayFieldsLinter(ERC7730Linter):
    """
    Validates display fields against reference ABIs fetched from Etherscan.

    For contract context:
      - Fetches ABI from Etherscan for each deployment
      - Validates that display field paths exist in the ABI
      - Validates that all ABI function params have display fields
      - Checks that all selectors in the ABI have corresponding display formats

    For EIP-712 context:
      - No schema available in v2 resolved model, so no validation is performed
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        match descriptor.context:
            case ResolvedEIP712Context():
                pass  # no schema to validate against in v2
            case ResolvedContractContext():
                self._validate_contract_display_fields(descriptor, out)

    @classmethod
    def _validate_contract_display_fields(cls, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        context = descriptor.context
        if not isinstance(context, ResolvedContractContext):
            return

        if (deployments := context.contract.deployments) is None:
            return

        # Try to fetch ABI from Etherscan for the first deployment that succeeds
        reference_abis = None
        explorer_url = None
        for deployment in deployments:
            try:
                if (abis := client.get_contract_abis(deployment.chainId, deployment.address)) is None:
                    continue
            except Exception as e:
                out.warning(
                    title="Could not fetch ABI",
                    message=f"Fetching reference ABI for chain id {deployment.chainId} failed, display fields will "
                    f"not be validated against ABI: {e}",
                )
                continue

            reference_abis = get_functions(abis)
            try:
                explorer_url = client.get_contract_explorer_url(deployment.chainId, deployment.address)
            except NotImplementedError:
                explorer_url = f"<chain id {deployment.chainId} address {deployment.address}>"
            break

        if reference_abis is None:
            return

        if reference_abis.proxy:
            return out.info(
                title="Proxy contract",
                message=f"Contract {explorer_url} is likely to be a proxy, validation of display fields skipped",
            )

        # Build ABI paths by selector
        abi_paths_by_selector: dict[str, set[DataPath]] = {}
        for selector, abi in reference_abis.functions.items():
            abi_paths_by_selector[selector] = compute_abi_schema_paths(abi)

        # Validate display field paths against ABI paths
        for selector, fmt in descriptor.display.formats.items():
            if selector not in abi_paths_by_selector:
                out.warning(
                    title="Unknown selector",
                    message=f"Selector {selector} in display formats not found in reference ABI (see {explorer_url}). "
                    f"This could indicate a custom function or a stale descriptor.",
                )
                continue

            format_paths = compute_format_schema_paths(fmt)
            abi_paths = abi_paths_by_selector[selector]

            # Check for display fields referencing non-existent ABI paths
            for path in format_paths.data_paths - abi_paths:
                out.error(
                    title="Invalid display field",
                    message=f"A display field is defined for `{path}`, but it does not exist in function "
                    f"{selector} ABI (see {explorer_url}). Please check the field path is valid.",
                )

            # Check for ABI paths without corresponding display fields
            for path in abi_paths - format_paths.data_paths:
                out.warning(
                    title="Missing display field",
                    message=f"No display field is defined for path `{path}` in function {selector} "
                    f"(see {explorer_url}).",
                )

        # Check selector exhaustiveness: all ABI functions should have display formats
        for selector, abi in reference_abis.functions.items():
            if selector not in descriptor.display.formats:
                out.warning(
                    title="Missing display format",
                    message=f"Function {compute_signature(abi)} (selector: {selector}) exists in reference ABI "
                    f"(see {explorer_url}) but has no display format defined in the descriptor.",
                )
