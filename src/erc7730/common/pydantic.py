import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from erc7730.common.json import read_json_with_includes

M = TypeVar("M", bound=BaseModel)


def model_from_json_file_with_includes(path: Path, model: type[M]) -> M:
    """
    Load a Pydantic model from a JSON file., including includes references
    """
    return model.model_validate(read_json_with_includes(path), strict=False)


def model_from_json_file_with_includes_or_none(path: Path, model: type[M]) -> M | None:
    """
    Load a Pydantic model from a JSON file, or None if file does not exist.
    """
    return model_from_json_file_with_includes(path, model) if os.path.isfile(path) else None


def json_file_from_model(model: type[M], obj: M) -> str:
    """Serialize pydantic model"""
    return model.model_dump_json(obj, by_alias=True, exclude_none=True)


def model_from_json_bytes(bytes: bytes, model: type[M]) -> M:
    """
    Load a Pydantic model from a JSON file content as an array of bytes.
    """
    return model.model_validate_json(bytes, strict=True)
