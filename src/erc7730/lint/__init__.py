from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import IntEnum, auto

from pydantic import BaseModel, FilePath

from erc7730.model.descriptor import ERC7730Descriptor


class ERC7730Linter(ABC):
    """
    Linter for ERC-7730 descriptors, inspects a (structurally valid) descriptor and emits notes, warnings, or
    errors.

    A linter may emit false positives or false negatives. It is up to the user to interpret the output.
    """

    @abstractmethod
    def lint(self, descriptor: ERC7730Descriptor, out: "OutputAdder") -> None:
        raise NotImplementedError()

    class Output(BaseModel):
        """ERC7730Linter output notice/warning/error."""

        class Level(IntEnum):
            """ERC7730Linter output level."""

            INFO = auto()
            WARNING = auto()
            ERROR = auto()

        file: FilePath | None = None
        line: int | None = None
        title: str
        message: str
        level: Level = Level.ERROR

    OutputAdder = Callable[[Output], None]
    """ERC7730Linter output sink."""
