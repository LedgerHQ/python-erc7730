from pathlib import Path
from typing import Annotated

from eip712 import EIP712DAppDescriptor
from typer import Argument, Exit, Option, Typer

from erc7730.common.output import ConsoleOutputAdder
from erc7730.common.pydantic import model_from_json_file_with_includes
from erc7730.convert.convert import convert_to_file_and_print_errors
from erc7730.convert.convert_eip712_to_erc7730 import EIP712toERC7730Converter
from erc7730.convert.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.convert.convert_erc7730_to_eip712 import ERC7730toEIP712Converter
from erc7730.lint.lint import lint_all_and_print_errors
from erc7730.model.input.descriptor import InputERC7730Descriptor

app = Typer(
    name="erc7730",
    no_args_is_help=True,
    help="""
    ERC-7730 tool.
    """,
)
convert_app = Typer(
    name="convert",
    no_args_is_help=True,
    short_help="Commands to convert descriptor files.",
    help="""
    Commands to convert descriptor files.
    """,
)
app.add_typer(convert_app)


@app.command(
    name="lint",
    short_help="Validate descriptor files.",
    help="""
    Validate descriptor files.
    """,
)
def lint(
    paths: Annotated[list[Path], Argument(help="The files or directory paths to lint")],
    gha: Annotated[bool, Option(help="Enable Github annotations output")] = False,
) -> None:
    if not lint_all_and_print_errors(paths, gha):
        raise Exit(1)


@convert_app.command(
    name="eip712-to-erc7730",
    short_help="Convert a legacy EIP-712 descriptor file to an ERC-7730 file.",
    help="""
    Convert a legacy EIP-712 descriptor file to an ERC-7730 file.
    """,
)
def convert_eip712_to_erc7730(
    input_eip712_path: Annotated[Path, Argument(help="The input EIP-712 file path")],
    output_erc7730_path: Annotated[Path, Argument(help="The output ERC-7730 file path")],
) -> None:
    if not convert_to_file_and_print_errors(
        input_descriptor=model_from_json_file_with_includes(input_eip712_path, EIP712DAppDescriptor),
        output_file=output_erc7730_path,
        converter=EIP712toERC7730Converter(),
    ):
        raise Exit(1)


@convert_app.command(
    name="erc7730-to-eip712",
    short_help="Convert an ERC-7730 file to a legacy EIP-712 descriptor file.",
    help="""
    Convert an ERC-7730 file to a legacy EIP-712 descriptor file (if applicable).
    """,
)
def convert_erc7730_to_eip712(
    input_erc7730_path: Annotated[Path, Argument(help="The input ERC-7730 file path")],
    output_eip712_path: Annotated[Path, Argument(help="The output EIP-712 file path")],
) -> None:
    input_descriptor = InputERC7730Descriptor.load(input_erc7730_path)
    resolved_descriptor = ERC7730InputToResolved().convert(input_descriptor, ConsoleOutputAdder())
    if resolved_descriptor is None or not convert_to_file_and_print_errors(
        input_descriptor=resolved_descriptor,
        output_file=output_eip712_path,
        converter=ERC7730toEIP712Converter(),
    ):
        raise Exit(1)


if __name__ == "__main__":
    app()
