import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, LiteralString, TypeVar

from pydantic import BaseModel, ValidationInfo, WrapValidator
from pydantic_core import PydanticCustomError

from erc7730.common.json import dict_to_json_file, dict_to_json_str, read_json_with_includes

_BaseModel = TypeVar("_BaseModel", bound=BaseModel)


def model_from_json_bytes(data: bytes, model: type[_BaseModel]) -> _BaseModel:
    """Load a Pydantic model from JSON content as an array of bytes."""
    return model.model_validate_json(data, strict=True)


def model_from_json_str(data: str, model: type[_BaseModel]) -> _BaseModel:
    """Load a Pydantic model from JSON content as an array of bytes."""
    return model.model_validate_json(data, strict=True)


def model_from_json_file_with_includes(path: Path, model: type[_BaseModel]) -> _BaseModel:
    """Load a Pydantic model from a JSON file, including references."""
    return model.model_validate(read_json_with_includes(path), strict=False)


def model_from_json_file_with_includes_or_none(path: Path, model: type[_BaseModel]) -> _BaseModel | None:
    """Load a Pydantic model from a JSON file, or None if file does not exist."""
    return model_from_json_file_with_includes(path, model) if os.path.isfile(path) else None


def model_to_json_dict(obj: _BaseModel) -> dict[str, Any]:
    """Serialize a pydantic model into a JSON dict."""
    return obj.model_dump(mode="json", by_alias=True, exclude_none=True)


def model_to_json_str(obj: _BaseModel) -> str:
    """Serialize a pydantic model into a JSON string."""
    return dict_to_json_str(model_to_json_dict(obj))


def model_to_json_file(path: Path, model: _BaseModel) -> None:
    """Write a model to a JSON file, creating parent directories as needed."""
    dict_to_json_file(path, model_to_json_dict(model))


@dataclass(frozen=True)
class ErrorTypeLabel(WrapValidator):
    """
    Wrapper validator that replaces all errors with a simple message "expected a <type label>".

    It is useful for annotating union types where pydantic returns multiple errors for each type it tries, or custom
    base types such as pattern validated strings to get more user-friendly errors.
    """

    def __init__(self, type_label: LiteralString) -> None:
        super().__init__(self._validator(type_label))

    @staticmethod
    def _validator(type_label: LiteralString) -> Callable[[Any, Any, ValidationInfo], Any]:
        def validate(v: Any, next_: Any, ctx: ValidationInfo) -> Any:
            try:
                return next_(v, ctx)
            except Exception:
                raise PydanticCustomError("custom_error", "expected a " + type_label) from None

        return validate
