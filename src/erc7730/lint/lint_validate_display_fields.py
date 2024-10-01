from typing import final, override

from erc7730.common.abi import compute_paths, compute_selector
from erc7730.lint import ERC7730Linter
from erc7730.lint.common.paths import compute_eip712_paths, compute_format_paths
from erc7730.model.resolved.context import EIP712JsonSchema, ResolvedContractContext, ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor


@final
class ValidateDisplayFieldsLinter(ERC7730Linter):
    """
    - for each field of schema/ABI, check that there is a display field
    - for each field, check that display configuration is relevant with field type
    """

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: ERC7730Linter.OutputAdder) -> None:
        self._validate_eip712_paths(descriptor, out)
        self._validate_abi_paths(descriptor, out)

    @classmethod
    def _validate_eip712_paths(cls, descriptor: ResolvedERC7730Descriptor, out: ERC7730Linter.OutputAdder) -> None:
        if isinstance(descriptor.context, ResolvedEIP712Context) and descriptor.context.eip712.schemas is not None:
            primary_types: set[str] = set()
            for schema in descriptor.context.eip712.schemas:
                if isinstance(schema, EIP712JsonSchema):
                    primary_types.add(schema.primaryType)
                    if schema.primaryType not in schema.types:
                        out(
                            ERC7730Linter.Output(
                                title="Invalid EIP712 Schema",
                                message=f"Primary type `{schema.primaryType}` not found in types.",
                                level=ERC7730Linter.Output.Level.ERROR,
                            )
                        )
                        continue
                    if schema.primaryType not in descriptor.display.formats:
                        out(
                            ERC7730Linter.Output(
                                title="Missing Display field",
                                message=f"Display field for primary type `{schema.primaryType}` is missing.",
                                level=ERC7730Linter.Output.Level.WARNING,
                            )
                        )
                        continue
                    eip712_paths = compute_eip712_paths(schema)
                    format_paths = compute_format_paths(descriptor.display.formats[schema.primaryType]).data_paths

                    for path in eip712_paths - format_paths:
                        out(
                            ERC7730Linter.Output(
                                title="Missing Display field",
                                message=f"Display field for path `{path}` is missing for message {schema.primaryType}.",
                                level=ERC7730Linter.Output.Level.WARNING,
                            )
                        )
                    for path in format_paths - eip712_paths:
                        out(
                            ERC7730Linter.Output(
                                title="Extra Display field",
                                message=f"Display field for path `{path}` is not in message {schema.primaryType}.",
                                level=ERC7730Linter.Output.Level.ERROR,
                            )
                        )

                else:
                    out(
                        ERC7730Linter.Output(
                            title="Missing EIP712 Schema",
                            message=f"EIP712 Schema is missing (found {schema})",
                            level=ERC7730Linter.Output.Level.ERROR,
                        )
                    )

            for fmt in descriptor.display.formats:
                if fmt not in primary_types:
                    out(
                        ERC7730Linter.Output(
                            title="Invalid Display field",
                            message=f"Format message `{fmt}` is not in EIP712 schemas.",
                            level=ERC7730Linter.Output.Level.ERROR,
                        )
                    )

    @classmethod
    def _validate_abi_paths(cls, descriptor: ResolvedERC7730Descriptor, out: ERC7730Linter.OutputAdder) -> None:
        if isinstance(descriptor.context, ResolvedContractContext):
            abi_paths_by_selector: dict[str, set[str]] = {}
            for abi in descriptor.context.contract.abi:
                if abi.type == "function":
                    abi_paths_by_selector[compute_selector(abi)] = compute_paths(abi)

            for selector, fmt in descriptor.display.formats.items():
                if selector not in abi_paths_by_selector:
                    out(
                        ERC7730Linter.Output(
                            title="Invalid selector",
                            message=f"Selector {selector} not found in ABI.",
                            level=ERC7730Linter.Output.Level.ERROR,
                        )
                    )
                    continue
                format_paths = compute_format_paths(fmt).data_paths
                abi_paths = abi_paths_by_selector[selector]

                for path in abi_paths - format_paths:
                    out(
                        ERC7730Linter.Output(
                            title="Missing Display field",
                            message=f"Display field for path `{path}` is missing for selector {selector}.",
                            level=ERC7730Linter.Output.Level.WARNING,
                        )
                    )
                for path in format_paths - abi_paths:
                    out(
                        ERC7730Linter.Output(
                            title="Invalid Display field",
                            message=f"Display field for path `{path}` is not in selector {selector}.",
                            level=ERC7730Linter.Output.Level.ERROR,
                        )
                    )
