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

DATA = Path(__file__).parent.parent / "convert" / "resolved" / "data"

DEPRECATED_ABI = DATA / "deprecated_abi_ignored_input.json"
DEPRECATED_SCHEMAS = DATA / "deprecated_schemas_ignored_input.json"
MINIMAL_CONTRACT = DATA / "minimal_contract_v2_input.json"
MINIMAL_EIP712 = DATA / "minimal_eip712_v2_input.json"


def error_titles(out: ListOutputAdder) -> list[str | None]:
    return [output.title for output in out.outputs if output.level == Output.Level.ERROR]


def load_with(path: Path, context_key: str, field: str, value: Any) -> InputERC7730Descriptor:
    """Load a descriptor file, with a deprecated context field added."""
    data = json.loads(path.read_text())
    data["context"][context_key][field] = value
    return InputERC7730Descriptor.model_validate(data, strict=False)


def lint(path: Path) -> ListOutputAdder:
    out = ListOutputAdder()
    validate_deprecated_fields(InputERC7730Descriptor.load(path), out)
    return out


@pytest.mark.parametrize("path", [MINIMAL_CONTRACT, MINIMAL_EIP712], ids=["contract", "eip712"])
def test_descriptor_without_deprecated_fields_is_accepted(path: Path) -> None:
    assert lint(path).outputs == []


def test_contract_abi_field_is_an_error() -> None:
    assert error_titles(lint(DEPRECATED_ABI)) == [DEPRECATED_ABI_TITLE]


def test_eip712_schemas_field_is_an_error() -> None:
    assert error_titles(lint(DEPRECATED_SCHEMAS)) == [DEPRECATED_SCHEMAS_TITLE]


def test_empty_contract_abi_field_is_an_error() -> None:
    """An empty ABI is still a set field: only a missing field is accepted."""
    out = ListOutputAdder()
    validate_deprecated_fields(load_with(MINIMAL_CONTRACT, "contract", "abi", []), out)
    assert error_titles(out) == [DEPRECATED_ABI_TITLE]


def test_empty_eip712_schemas_field_is_an_error() -> None:
    """An empty schemas list is still a set field: only a missing field is accepted."""
    out = ListOutputAdder()
    validate_deprecated_fields(load_with(MINIMAL_EIP712, "eip712", "schemas", []), out)
    assert error_titles(out) == [DEPRECATED_SCHEMAS_TITLE]


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
