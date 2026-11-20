from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InvalidDescriptor:
    message: str


@dataclass(frozen=True)
class Diagnostic:
    level: str
    title: str | None
    message: str


@dataclass(frozen=True)
class Compiled:
    descriptors: tuple[dict[str, Any], ...]
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class ConversionFailed:
    diagnostics: tuple[Diagnostic, ...]


CompileResult = Compiled | ConversionFailed | InvalidDescriptor
