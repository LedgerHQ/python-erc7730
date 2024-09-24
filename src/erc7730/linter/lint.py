from pathlib import Path

from erc7730 import ERC_7730_REGISTRY_CALLDATA_PREFIX, ERC_7730_REGISTRY_EIP712_PREFIX
from erc7730.common.pydantic import model_from_json_file_with_includes
from erc7730.linter import ERC7730Linter
from erc7730.linter.linter_base import MultiLinter
from erc7730.linter.linter_transaction_type_classifier_ai import ClassifyTransactionTypeLinter
from erc7730.linter.linter_validate_abi import ValidateABILinter
from erc7730.linter.linter_validate_display_fields import ValidateDisplayFieldsLinter
from erc7730.model.erc7730_descriptor import ERC7730Descriptor
from rich import print

from erc7730.model.utils import resolve_external_references


def lint_all(paths: list[Path]) -> list[ERC7730Linter.Output]:
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
    print(f"checking {path}...")

    def adder(output: ERC7730Linter.Output) -> None:
        out(output.model_copy(update={"file": path}))

    try:
        descriptor = model_from_json_file_with_includes(path, ERC7730Descriptor)
        descriptor = resolve_external_references(descriptor)
        linter.lint(descriptor, adder)
    except Exception as e:
        out(
            ERC7730Linter.Output(
                file=path, title="Failed to parse", message=str(e), level=ERC7730Linter.Output.Level.ERROR
            )
        )
