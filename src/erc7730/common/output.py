from abc import ABC, abstractmethod
from builtins import print as builtin_print
from enum import IntEnum, auto
from typing import assert_never, final, override

from pydantic import BaseModel, FilePath
from rich import print


class Output(BaseModel):
    """An output info/debug/warning/error."""

    class Level(IntEnum):
        """ERC7730Linter output level."""

        DEBUG = auto()
        INFO = auto()
        WARNING = auto()
        ERROR = auto()

    file: FilePath | None
    line: int | None
    title: str | None
    message: str
    level: Level = Level.ERROR


class OutputAdder(ABC):
    """An output debug/info/warning/error sink."""

    has_infos = False
    has_warnings = False
    has_errors = False

    @abstractmethod
    def debug(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    def info(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    def warning(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    def error(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        raise NotImplementedError()


@final
class ListOutputAdder(OutputAdder, BaseModel):
    """An output adder that stores outputs in a list."""

    outputs: list[Output] = []

    @override
    def debug(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.outputs.append(Output(file=file, line=line, title=title, message=message, level=Output.Level.DEBUG))

    @override
    def info(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_infos = True
        self.outputs.append(Output(file=file, line=line, title=title, message=message, level=Output.Level.INFO))

    @override
    def warning(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_warnings = True
        self.outputs.append(Output(file=file, line=line, title=title, message=message, level=Output.Level.WARNING))

    @override
    def error(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_errors = True
        self.outputs.append(Output(file=file, line=line, title=title, message=message, level=Output.Level.ERROR))


@final
class ConsoleOutputAdder(OutputAdder):
    """An output adder that prints to the console."""

    @override
    def debug(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self._log(Output.Level.DEBUG, message, file, line, title)

    @override
    def info(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_infos = True
        self._log(Output.Level.INFO, message, file, line, title)

    @override
    def warning(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_warnings = True
        self._log(Output.Level.WARNING, message, file, line, title)

    @override
    def error(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_errors = True
        self._log(Output.Level.ERROR, message, file, line, title)

    @classmethod
    def _log(
        cls,
        level: Output.Level,
        message: str,
        file: FilePath | None = None,
        line: int | None = None,
        title: str | None = None,
    ) -> None:
        match level:
            case Output.Level.DEBUG:
                style = "bold"
            case Output.Level.INFO:
                style = "blue"
            case Output.Level.WARNING:
                style = "yellow"
            case Output.Level.ERROR:
                style = "red"
            case _:
                assert_never(level)

        log = f"[{style}]{level.name}: "
        if line is not None:
            log += f"line {line}: "
        if title is not None:
            log += f"{title}: "
        log += f"[/{style}]{message}"

        print(log)


@final
class GithubAnnotationsAdder(OutputAdder):
    """An output adder that formats errors to be parsed as Github annotations."""

    @override
    def debug(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        pass

    @override
    def info(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_infos = True
        self._log(Output.Level.INFO, message, file, line, title)

    @override
    def warning(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_warnings = True
        self._log(Output.Level.WARNING, message, file, line, title)

    @override
    def error(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.has_errors = True
        self._log(Output.Level.ERROR, message, file, line, title)

    @classmethod
    def _log(
        cls,
        level: Output.Level,
        message: str,
        file: FilePath | None = None,
        line: int | None = None,
        title: str | None = None,
    ) -> None:
        match level:
            case Output.Level.DEBUG:
                raise RuntimeError("GithubAnnotationsAdder does not support debug messages")
            case Output.Level.INFO:
                lvl = "notice"
            case Output.Level.WARNING:
                lvl = "warning"
            case Output.Level.ERROR:
                lvl = "error"
            case _:
                assert_never(level)

        log = f"::{lvl} "
        if file is not None:
            log += f"file={file}"
        if line is not None:
            log += f",line={line}"
        if title is not None:
            log += f",title={title}"
        message_formatted = message.replace("\n", "%0A")
        log += f"::{message_formatted}"

        builtin_print(log)


class FileOutputAdder(OutputAdder):
    """An output adder wrapper that adds a specific file to all outputs."""

    def __init__(self, delegate: OutputAdder, file: FilePath) -> None:
        self.delegate: OutputAdder = delegate
        self.file: FilePath = file

    def debug(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.delegate.debug(message=message, file=self.file, line=line, title=title)

    def info(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.delegate.info(message=message, file=self.file, line=line, title=title)

    def warning(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.delegate.warning(message=message, file=self.file, line=line, title=title)

    def error(
        self, message: str, file: FilePath | None = None, line: int | None = None, title: str | None = None
    ) -> None:
        self.delegate.error(message=message, file=self.file, line=line, title=title)
