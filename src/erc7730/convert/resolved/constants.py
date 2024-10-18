from abc import ABC, abstractmethod
from typing import Any

from typing_extensions import TypeVar

from erc7730.model.metadata import Metadata
from erc7730.model.paths import DescriptorPath, Field
from erc7730.model.paths.path_ops import descriptor_path_append, descriptor_path_starts_with

_T = TypeVar("_T", covariant=True)


class ConstantProvider(ABC):
    @abstractmethod
    def get(self, path: DescriptorPath) -> Any:
        raise NotImplementedError()

    def resolve(self, value: _T | DescriptorPath) -> _T:
        if isinstance(value, DescriptorPath):
            return self.get(value)
        return value

    def resolve_or_none(self, value: _T | DescriptorPath | None) -> _T | None:
        if value is None:
            return None
        return self.resolve(value)


class MetadataConstantsProvider(ConstantProvider):
    CONSTANTS_PATH = DescriptorPath(elements=[Field(identifier="metadata"), Field(identifier="constants")])

    def __init__(self, metadata: Metadata) -> None:
        self.values: dict[DescriptorPath, Any] = {
            descriptor_path_append(self.CONSTANTS_PATH, Field(identifier=key)): value
            for key, value in (metadata.constants or {}).items()
        }

    def get(self, path: DescriptorPath) -> Any:
        if not descriptor_path_starts_with(path, self.CONSTANTS_PATH):
            raise ValueError(f"Constants are only allowed in {self.CONSTANTS_PATH}, got {path}")
        if (value := self.values.get(path)) is not None:
            return value
        raise ValueError(f"No constant defined at path {path}")
