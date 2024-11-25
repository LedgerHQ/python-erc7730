from pathlib import Path

import pytest

from erc7730.common.output import SetOutputAdder
from erc7730.lint.lint import lint_all, lint_all_and_print_errors
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS

RESOURCES = Path(__file__).resolve().parent / "resources"


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_registry_files(input_file: Path) -> None:
    """
    Test linting ERC-7730 registry files, which should all be valid at all times.
    """

    # TODO: these descriptors use literal constants instead of token paths, which is not supported yet
    if input_file.name in {"calldata-OssifiableProxy.json", "calldata-wstETH.json", "calldata-usdt.json"}:
        pytest.skip("Descriptor uses literal constants instead of token paths, which is not supported yet")

    assert lint_all_and_print_errors([input_file])


def test_unused_definition_detected_by_linter() -> None:
    """
    Test unused field definition is detected within an ERC-7730 file
    """
    output_adder = SetOutputAdder()

    input_file = RESOURCES / "calldata-unused-definitions.json"

    lint_all([input_file], output_adder)

    assert output_adder.has_errors is True

    assert "Unused field definition" in (set(map(lambda x: x.title, output_adder.outputs)))
