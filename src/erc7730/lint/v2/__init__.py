from abc import ABC, abstractmethod
from typing import final, override

from erc7730.common.output import OutputAdder
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor


class ERC7730Linter(ABC):
    """
    Linter for ERC-7730 v2 descriptors, inspects a (structurally valid) resolved v2 descriptor and emits notes,
    warnings, or errors.

    A linter may emit false positives or false negatives. It is up to the user to interpret the output.
    """

    @abstractmethod
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        raise NotImplementedError()


@final
class MultiLinter(ERC7730Linter):
    """A linter that runs multiple v2 linters in sequence."""

    def __init__(self, linters: list[ERC7730Linter]):
        self.linters = linters

    @override
    def lint(self, descriptor: ResolvedERC7730Descriptor, out: OutputAdder) -> None:
        for linter in self.linters:
            linter.lint(descriptor, out)
