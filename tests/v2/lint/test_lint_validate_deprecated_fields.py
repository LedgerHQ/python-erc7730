import json
from pathlib import Path
from typing import Any

import pytest

from erc7730.common.output import ListOutputAdder, Output
from erc7730.lint.v2.lint import lint_file
from erc7730.lint.v2.lint_validate_deprecated_fields import (
    DEPRECATED_ABI_TITLE,
    DEPRECATED_SCHEMAS_TITLE,
    ValidateDeprecatedFieldsLinter,
    validate_deprecated_fields,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.files import TEST_RESOURCES

LINT_RESOURCES = TEST_RESOURCES / "lint"

DEPRECATED_ABI = LINT_RESOURCES / "calldata-deprecated-abi.json"
DEPRECATED_SCHEMAS = LINT_RESOURCES / "eip712-deprecated-schemas.json"
CONTRACT = LINT_RESOURCES / "calldata-two-deployments.json"
EIP712 = LINT_RESOURCES / "eip712-minimal.json"


def error_titles(out: ListOutputAdder) -> list[str | None]:
    return [output.title for output in out.outputs if output.level == Output.Level.ERROR]


def load_with(path: Path, context_key: str, field: str, value: Any) -> InputERC7730Descriptor:
    """Load a descriptor file, with a deprecated context field added."""
    data = json.loads(path.read_text())
    data["context"][context_key][field] = value
    return InputERC7730Descriptor.model_validate(data, strict=False)


def lint(descriptor: InputERC7730Descriptor) -> ListOutputAdder:
    out = ListOutputAdder()
    validate_deprecated_fields(descriptor, out)
    return out


@pytest.mark.parametrize("path", [CONTRACT, EIP712], ids=["contract", "eip712"])
def test_descriptor_without_deprecated_fields_is_accepted(path: Path) -> None:
    assert lint(InputERC7730Descriptor.load(path)).outputs == []


def test_contract_abi_field_is_an_error() -> None:
    assert error_titles(lint(InputERC7730Descriptor.load(DEPRECATED_ABI))) == [DEPRECATED_ABI_TITLE]


def test_eip712_schemas_field_is_an_error() -> None:
    assert error_titles(lint(InputERC7730Descriptor.load(DEPRECATED_SCHEMAS))) == [DEPRECATED_SCHEMAS_TITLE]


@pytest.mark.parametrize("value", [[], None], ids=["empty", "null"])
def test_contract_abi_field_with_no_content_is_an_error(value: Any) -> None:
    """An empty or null ABI is still a set field: only a missing field is accepted."""
    assert error_titles(lint(load_with(CONTRACT, "contract", "abi", value))) == [DEPRECATED_ABI_TITLE]


@pytest.mark.parametrize("value", [[], None], ids=["empty", "null"])
def test_eip712_schemas_field_with_no_content_is_an_error(value: Any) -> None:
    """An empty or null schemas list is still a set field: only a missing field is accepted."""
    assert error_titles(lint(load_with(EIP712, "eip712", "schemas", value))) == [DEPRECATED_SCHEMAS_TITLE]


@pytest.mark.parametrize(
    "path,title",
    [(DEPRECATED_ABI, DEPRECATED_ABI_TITLE), (DEPRECATED_SCHEMAS, DEPRECATED_SCHEMAS_TITLE)],
    ids=["abi", "schemas"],
)
def test_lint_file_reports_the_deprecated_field_as_an_error(path: Path, title: str) -> None:
    """The deprecated field is reported when linting a file, even though resolution drops it."""
    out = ListOutputAdder()
    lint_file(path, ValidateDeprecatedFieldsLinter(), out)
    assert out.has_errors
    assert error_titles(out) == [title]
