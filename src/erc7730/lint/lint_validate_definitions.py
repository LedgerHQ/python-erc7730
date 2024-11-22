from typing import final, override

from erc7730.common.output import OutputAdder
from erc7730.lint import ERC7730Linter
from erc7730.model.resolved.context import ResolvedEIP712Context
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor


@final
class DefinitionLinter(ERC7730Linter):
    """Check that parameters under definitions are used in formats section"""

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        if isinstance(descriptor.context, ResolvedEIP712Context) and descriptor.display.definitions is not None:
            for name, _ in descriptor.display.definitions.items():
                found = False
                for _, format in descriptor.display.formats.items():
                    if found is False:
                        for field in format.fields:
                            if field.path == name:
                                found = True
                if found is False:
                    out.error(
                        title="Unused field definition",
                        message=f"Field {name} is not used in descriptor formats.",
                    )
