import os
from collections.abc import Generator
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from pydantic import ValidationError
from rich import print

from erc7730 import ERC_7730_REGISTRY_CALLDATA_PREFIX, ERC_7730_REGISTRY_EIP712_PREFIX
from erc7730.common.output import BufferAdder, ConsoleOutputAdder, FileOutputAdder, GithubAnnotationsAdder, OutputAdder
from erc7730.convert.resolved.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint import ERC7730Linter
from erc7730.lint.lint_base import MultiLinter
from erc7730.lint.lint_transaction_type_classifier import ClassifyTransactionTypeLinter
from erc7730.lint.lint_validate_abi import ValidateABILinter
from erc7730.lint.lint_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.model.input.descriptor import InputERC7730Descriptor


def lint_all_and_print_errors(paths: list[Path], gha: bool = False) -> bool:
    out = GithubAnnotationsAdder() if gha else ConsoleOutputAdder()

    count = lint_all(paths, out)

    if out.has_errors:
        print(f"[bold][red]checked {count} descriptor files, some errors found ❌[/red][/bold]")
        return False

    if out.has_warnings:
        print(f"[bold][yellow]checked {count} descriptor files, some warnings found ⚠️[/yellow][/bold]")
        return True

    print(f"[bold][green]checked {count} descriptor files, no errors found ✅[/green][/bold]")
    return True


def lint_all(paths: list[Path], out: OutputAdder) -> int:
    """
    Lint all ERC-7730 descriptor files at given paths.

    Paths can be files or directories, in which case all JSON files in the directory are recursively linted.

    :param paths: paths to apply linter on
    :param out: output adder
    :return: number of files checked
    """
    linter = MultiLinter(
        [
            ValidateABILinter(),
            ValidateDisplayFieldsLinter(),
            ClassifyTransactionTypeLinter(),
        ]
    )

    def get_descriptor_files() -> Generator[Path, None, None]:
        for path in paths:
            if path.is_file():
                yield path
            elif path.is_dir():
                for file in path.rglob("*.json"):
                    if file.name.startswith(ERC_7730_REGISTRY_CALLDATA_PREFIX) or file.name.startswith(
                        ERC_7730_REGISTRY_EIP712_PREFIX
                    ):
                        yield file
            else:
                raise ValueError(f"Invalid path: {path}")

    files = list(get_descriptor_files())

    if len(files) <= 1 or not (root_path := os.path.commonprefix(files)):
        root_path = None

    def label(f: Path) -> Path | None:
        return f.relative_to(root_path) if root_path is not None else None

    with ThreadPoolExecutor() as executor:
        for future in (executor.submit(lint_file, file, linter, out, label(file)) for file in files):
            future.result()

    return len(files)


def lint_file(path: Path, linter: ERC7730Linter, out: OutputAdder, show_as: Path | None = None) -> None:
    """
    Lint a single ERC-7730 descriptor file.

    :param path: ERC-7730 descriptor file path
    :param show_as: if provided, print this label instead of the file path
    :param linter: linter instance
    :param out: error handler
    """

    label = path if show_as is None else show_as
    file_out = FileOutputAdder(delegate=out, file=path)

    with BufferAdder(file_out, prolog=f"➡️ checking [bold]{label}[/bold]…", epilog="") as out:
        try:
            input_descriptor = InputERC7730Descriptor.load(path)
            resolved_descriptor = ERC7730InputToResolved().convert(input_descriptor, out)
            if resolved_descriptor is not None:
                linter.lint(resolved_descriptor, out)
        except ValidationError as e:
            for ex in e.errors(include_url=False, include_context=True, include_input=True):
                loc = ex["loc"]
                if loc == ():
                    out.error(title="Validation error", message=str(ex))
                else:
                    loc_str = ".".join(map(str, loc))
                    out.error(title=f"{loc_str}", message=ex["msg"])
        except Exception as e:
            # TODO unwrap pydantic validation errors here to provide more user-friendly error messages
            out.error(title="Failed to parse descriptor", message=str(e))
