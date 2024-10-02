from builtins import print as builtin_print
from pathlib import Path

from rich import print

from erc7730 import ERC_7730_REGISTRY_CALLDATA_PREFIX, ERC_7730_REGISTRY_EIP712_PREFIX
from erc7730.convert import ERC7730Converter
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.lint import ERC7730Linter
from erc7730.lint.lint_base import MultiLinter
from erc7730.lint.lint_transaction_type_classifier import ClassifyTransactionTypeLinter
from erc7730.lint.lint_validate_abi import ValidateABILinter
from erc7730.lint.lint_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.model.input.descriptor import InputERC7730Descriptor


def lint_all_and_print_errors(
    paths: list[Path],
    gha: bool,
) -> bool:
    if outputs := lint_all(paths):
        for output in outputs:
            p = output.file.name if output.file is not None else "unknown file"
            if gha:
                msg = output.message.replace("\n", "%0A")
                match output.level:
                    case ERC7730Linter.Output.Level.INFO:
                        builtin_print(f"::notice file={output.file},title={output.title}::{msg}")
                    case ERC7730Linter.Output.Level.WARNING:
                        builtin_print(f"::warning file={output.file},title={output.title}::{msg}")
                    case ERC7730Linter.Output.Level.ERROR:
                        builtin_print(f"::error file={output.file},title={output.title}::{msg}")
            else:
                match output.level:
                    case ERC7730Linter.Output.Level.INFO:
                        print(f"[blue]{p}: {output.level.name}: {output.title}[/blue]\n    {output.message}")
                    case ERC7730Linter.Output.Level.WARNING:
                        print(f"[yellow]{p}: {output.level.name}: {output.title}[/yellow]\n    {output.message}")
                    case ERC7730Linter.Output.Level.ERROR:
                        print(f"[red]{p}: {output.level.name}: {output.title}[/red]\n    {output.message}")
        return False

    print("[green]no issues found ✅[/green]")
    return True


def lint_all(paths: list[Path]) -> list[ERC7730Linter.Output]:
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

    outputs: list[ERC7730Linter.Output] = []

    for path in paths:
        if path.is_file():
            lint_file(path, linter, outputs.append)
        elif path.is_dir():
            for file in path.rglob("*.json"):
                if file.name.startswith(ERC_7730_REGISTRY_CALLDATA_PREFIX) or file.name.startswith(
                    ERC_7730_REGISTRY_EIP712_PREFIX
                ):
                    lint_file(file, linter, outputs.append)
        else:
            raise ValueError(f"Invalid path: {path}")

    return outputs


def lint_file(path: Path, linter: ERC7730Linter, out: ERC7730Linter.OutputAdder) -> None:
    """
    Lint a single ERC-7730 descriptor file.

    :param path: ERC-7730 descriptor file path
    :param linter: linter instance
    :param out: error handler
    """
    print(f"[italic]checking {path}...[/italic]")

    def adder(output: ERC7730Linter.Output) -> None:
        out(output.model_copy(update={"file": path}))

    try:
        input_descriptor = InputERC7730Descriptor.load(path)
        resolved_descriptor = ERC7730InputToResolved().convert(input_descriptor, _output_adapter(adder))
        if resolved_descriptor is not None:
            linter.lint(resolved_descriptor, adder)
    except Exception as e:
        # TODO unwrap pydantic validation errors here to provide more user-friendly error messages

        out(
            ERC7730Linter.Output(
                file=path, title="Failed to parse descriptor", message=str(e), level=ERC7730Linter.Output.Level.ERROR
            )
        )


def _output_adapter(out: ERC7730Linter.OutputAdder) -> ERC7730Converter.ErrorAdder:
    class ErrorAdder(ERC7730Converter.ErrorAdder):
        def warning(self, message: str) -> None:
            out(
                ERC7730Linter.Output(
                    title="Resolution error",
                    message=message,
                    level=ERC7730Linter.Output.Level.WARNING,
                )
            )

        def error(self, message: str) -> None:
            out(
                ERC7730Linter.Output(
                    title="Resolution error",
                    message=message,
                    level=ERC7730Linter.Output.Level.ERROR,
                )
            )

    return ErrorAdder()
