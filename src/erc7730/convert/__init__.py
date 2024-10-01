from abc import ABC, abstractmethod
from enum import IntEnum, auto
from typing import Generic, TypeVar

from pydantic import BaseModel

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

            WARNING = auto()
            """Indicates a non-fatal error: descriptor can be partially converted, but some parts will be lost."""

            ERROR = auto()
            """Indicates a fatal error: descriptor cannot be converted."""

        level: Level
        message: str

    class ErrorAdder(ABC):
        """ERC7730Converter output sink."""

        @abstractmethod
        def warning(self, message: str) -> None:
            raise NotImplementedError()

        @abstractmethod
        def error(self, message: str) -> None:
            raise NotImplementedError()
