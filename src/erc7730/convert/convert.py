from pathlib import Path

from rich import print

from erc7730.common.pydantic import model_to_json_file
from erc7730.convert import ERC7730Converter, InputType, OutputType


def convert_to_file_and_print_errors(
    input_descriptor: InputType, output_file: Path, converter: ERC7730Converter[InputType, OutputType]
) -> bool:
    """
    Convert an input descriptor to an output file using a converter, and print any errors encountered.

    :param input_descriptor: loaded, valid input descriptor
    :param output_file: output file path (overwritten if already exists)
    :param converter: converter to use
    :return: True if output file was written (if no errors, or only non-fatal errors encountered)
    """
    if (output_descriptor := convert_and_print_errors(input_descriptor, converter)) is not None:
        model_to_json_file(output_file, output_descriptor)
        print("[green]Output descriptor file generated ✅[/green]")
        return True

    print("[red]Conversion failed ❌[/red]")
    return False


def convert_and_print_errors(
    input_descriptor: InputType, converter: ERC7730Converter[InputType, OutputType]
) -> OutputType | None:
    """
    Convert an input descriptor using a converter, print any errors encountered, and return the result model.

    :param input_descriptor: loaded, valid input descriptor
    :param converter: converter to use
    :return: output descriptor (if no errors, or only non-fatal errors encountered), None otherwise
    """
    errors: list[ERC7730Converter.Error] = []

    result = converter.convert(input_descriptor, errors.append)

    for error in errors:
        match error.level:
            case ERC7730Converter.Error.Level.ERROR:
                print(f"[yellow][bold]{error.level}: [/bold]{error.message}[/yellow]")
            case ERC7730Converter.Error.Level.FATAL:
                print(f"[red][bold]{error.level}: [/bold]{error.message}[/red]")

    return result
