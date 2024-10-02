import os
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from erc7730.common.json import read_json_with_includes

ModelType = TypeVar("ModelType", bound=BaseModel)


def model_from_json_bytes(data: bytes, model: type[ModelType]) -> ModelType:
    """Load a Pydantic model from JSON content as an array of bytes."""
    return model.model_validate_json(data, strict=True)


def model_from_json_str(data: str, model: type[ModelType]) -> ModelType:
    """Load a Pydantic model from JSON content as an array of bytes."""
    return model.model_validate_json(data, strict=True)


def model_from_json_file_with_includes(path: Path, model: type[ModelType]) -> ModelType:
    """Load a Pydantic model from a JSON file, including references."""
    return model.model_validate(read_json_with_includes(path), strict=False)


def model_from_json_file_with_includes_or_none(path: Path, model: type[ModelType]) -> ModelType | None:
    """Load a Pydantic model from a JSON file, or None if file does not exist."""
    return model_from_json_file_with_includes(path, model) if os.path.isfile(path) else None


def model_to_json_dict(obj: ModelType) -> dict[str, Any]:
    """Serialize a pydantic model into a JSON string."""
    return obj.model_dump(by_alias=True, exclude_none=True)


def model_to_json_str(obj: ModelType) -> str:
    """Serialize a pydantic model into a JSON string."""
    return obj.model_dump_json(by_alias=True, exclude_none=True, indent=2)


def model_to_json_file(path: Path, model: ModelType) -> None:
    """Write a model to a JSON file, creating parent directories as needed."""
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(model_to_json_str(model))
        f.write("\n")
