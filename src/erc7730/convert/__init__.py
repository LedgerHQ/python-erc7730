from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import IntEnum, auto
from typing import Generic, TypeVar

from pydantic import BaseModel

from erc7730.model.descriptor import ERC7730Descriptor

InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel)


class ERC7730Converter(ABC, Generic[InputType, OutputType]):
    """
    Converter from/to ERC-7730 descriptor.

    A converter may fail partially, in which case it should emit errors with ERROR level, or totally, in which case it
    should emit errors with FATAL level.
    """

    @abstractmethod
    def convert(self, descriptor: InputType, error: "ErrorAdder") -> OutputType | None:
        """
        Convert a descriptor from/to ERC-7730.

        Conversion may fail partially, in which case it should emit errors with ERROR level, or totally, in which case
        it should emit errors with FATAL level.

        :param descriptor: input descriptor to convert
        :param error: error sink
        :return: converted descriptor, or None if conversion failed
        """
        raise NotImplementedError()

    class Error(BaseModel):
        """ERC7730Converter output errors."""

        class Level(IntEnum):
            """ERC7730Converter error level."""

            ERROR = auto()
            """Indicates a non-fatal error: descriptor can be partially converted, but some parts will be lost."""

            FATAL = auto()
            """Indicates a fatal error: descriptor cannot be converted."""

        level: Level = Level.ERROR
        message: str

    ErrorAdder = Callable[[Error], None]
    """ERC7730Converter output sink."""


class FromERC7730Converter(ERC7730Converter[ERC7730Descriptor, OutputType], ABC):
    """Converter from ERC-7730 to another format."""


class ToERC7730Converter(ERC7730Converter[InputType, ERC7730Descriptor], ABC):
    """Converter from another format to ERC-7730."""
