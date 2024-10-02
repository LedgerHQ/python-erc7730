from pathlib import Path

from rich import print

from erc7730 import ERC_7730_REGISTRY_CALLDATA_PREFIX, ERC_7730_REGISTRY_EIP712_PREFIX
from erc7730.common.output import ConsoleOutputAdder, GithubAnnotationsAdder, OutputAdder
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint import ERC7730Linter
from erc7730.lint.lint_base import MultiLinter
from erc7730.lint.lint_transaction_type_classifier import ClassifyTransactionTypeLinter
from erc7730.lint.lint_validate_abi import ValidateABILinter
from erc7730.lint.lint_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.model.input.descriptor import InputERC7730Descriptor


def lint_all_and_print_errors(paths: list[Path], gha: bool) -> bool:
    # FIXME adder must retain error state
    lint_all(paths, GithubAnnotationsAdder() if gha else ConsoleOutputAdder())
    print("[green]no issues found ✅[/green]")
    return True


def lint_all(paths: list[Path], out: OutputAdder) -> None:
    """
    Lint all ERC-7730 descriptor files at given paths.

    Paths can be files or directories, in which case all JSON files in the directory are recursively linted.

    :param paths: paths to apply linter on
    :return: output errors
    """
    linter = MultiLinter(
        [
            ValidateABILinter(),
            ValidateDisplayFieldsLinter(),
            ClassifyTransactionTypeLinter(),
        ]
    )

    for path in paths:
        if path.is_file():
            lint_file(path, linter, out)
        elif path.is_dir():
            for file in path.rglob("*.json"):
                if file.name.startswith(ERC_7730_REGISTRY_CALLDATA_PREFIX) or file.name.startswith(
                    ERC_7730_REGISTRY_EIP712_PREFIX
                ):
                    lint_file(file, linter, out)
        else:
            raise ValueError(f"Invalid path: {path}")


def lint_file(path: Path, linter: ERC7730Linter, out: OutputAdder) -> None:
    """
    Lint a single ERC-7730 descriptor file.

    :param path: ERC-7730 descriptor file path
    :param linter: linter instance
    :param out: error handler
    """
    print(f"[italic]checking {path}...[/italic]")

    # TODO wrap adder to add file path to all errors

    try:
        input_descriptor = InputERC7730Descriptor.load(path)
        resolved_descriptor = ERC7730InputToResolved().convert(input_descriptor, out)
        if resolved_descriptor is not None:
            linter.lint(resolved_descriptor, out)
    except Exception as e:
        # TODO unwrap pydantic validation errors here to provide more user-friendly error messages
        out.error(file=path, title="Failed to parse descriptor", message=str(e))
