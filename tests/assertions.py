import json
from typing import Any

import jsonschema
from prettydiff import print_diff

from erc7730.common.pydantic import ModelType, model_to_json_str


def assert_dict_equals(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    """Assert dictionaries are equal, pretty printing differences to console."""
    if expected != actual:
        print_diff(expected, actual)
        raise AssertionError("Dictionaries are not equal")


def assert_json_str_equals(expected: str, actual: str) -> None:
    """Assert deserialized JSON strings are equal."""
    assert_dict_equals(json.loads(expected), json.loads(actual))


def assert_model_json_equals(expected: ModelType, actual: ModelType) -> None:
    """Assert models serialize to same JSON, pretty printing differences to console."""
    assert_json_str_equals(model_to_json_str(expected), model_to_json_str(actual))


def assert_model_json_schema(model: ModelType, schema: Any) -> None:
    """Assert model is valid against JSON schema."""
    try:
        jsonschema.validate(instance=json.loads(model_to_json_str(model)), schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        raise AssertionError("Document does not respect JSON schema") from e
