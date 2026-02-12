import os
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from rich import print

from erc7730.common.output import (
    AddFileOutputAdder,
    BufferAdder,
    ConsoleOutputAdder,
    DropFileOutputAdder,
    ExceptionsToOutput,
    GithubAnnotationsAdder,
    OutputAdder,
)
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint.v2 import ERC7730Linter, MultiLinter
from erc7730.lint.v2.lint_transaction_type_classifier import ClassifyTransactionTypeLinter
from erc7730.lint.v2.lint_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.lint.v2.lint_validate_max_length import ValidateMaxLengthLinter
from erc7730.list.list import get_erc7730_files
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor


def lint_all_and_print_errors(paths: list[Path], gha: bool = False) -> bool:
    """Lint all ERC-7730 v2 descriptor files at given paths and print results."""
    out = GithubAnnotationsAdder() if gha else DropFileOutputAdder(delegate=ConsoleOutputAdder())

    count = lint_all(paths, out)

    if out.has_errors:
        print(f"[bold][red]checked {count} v2 descriptor files, some errors found ❌[/red][/bold]")
        return False

    if out.has_warnings:
        print(f"[bold][yellow]checked {count} v2 descriptor files, some warnings found ⚠️[/yellow][/bold]")
        return True

    print(f"[bold][green]checked {count} v2 descriptor files, no errors found ✅[/green][/bold]")
    return True


def lint_all(paths: list[Path], out: OutputAdder) -> int:
    """
    Lint all ERC-7730 v2 descriptor files at given paths.

    Paths can be files or directories, in which case all JSON files in the directory are recursively linted.

    :param paths: paths to apply linter on
    :param out: output adder
    :return: number of files checked
    """
    linter = MultiLinter([ValidateDisplayFieldsLinter(), ClassifyTransactionTypeLinter(), ValidateMaxLengthLinter()])

    files = list(get_erc7730_files(*paths, out=out))

    if len(files) <= 1 or not (root_path := os.path.commonpath(files)):
        root_path = None

    def label(f: Path) -> Path | None:
        return f.relative_to(root_path) if root_path is not None else None

    if len(files) > 1:
        print(f"🔍 checking {len(files)} v2 descriptor files…\n")

    with ThreadPoolExecutor() as executor:
        for future in (executor.submit(lint_file, file, linter, out, label(file)) for file in files):
            future.result()

    return len(files)


def lint_file(path: Path, linter: ERC7730Linter, out: OutputAdder, show_as: Path | None = None) -> None:
    """
    Lint a single ERC-7730 v2 descriptor file.

    :param path: ERC-7730 v2 descriptor file path
    :param show_as: if provided, print this label instead of the file path
    :param linter: v2 linter instance
    :param out: error handler
    """

    label = path if show_as is None else show_as
    file_out = AddFileOutputAdder(delegate=out, file=path)

    with BufferAdder(file_out, prolog=f"➡️ checking [bold]{label}[/bold]…", epilog="") as out, ExceptionsToOutput(out):
        input_descriptor = InputERC7730Descriptor.load(path)
        resolved_descriptor = ERC7730InputToResolved().convert(input_descriptor, out)
        if resolved_descriptor is not None:
            linter.lint(resolved_descriptor, out)
