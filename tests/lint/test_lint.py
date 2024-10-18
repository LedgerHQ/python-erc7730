from pathlib import Path

import pytest

from erc7730.lint.lint import lint_all_and_print_errors
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_registry_files(input_file: Path) -> None:
    """
    Test linting ERC-7730 registry files, which should all be valid at all times.
    """
    assert lint_all_and_print_errors([input_file])
