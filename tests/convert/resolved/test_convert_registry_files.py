from pathlib import Path

import pytest

from erc7730.convert.convert import convert_and_raise_errors
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_registry_files(input_file: Path) -> None:
    """
    Test converting ERC-7730 registry files from input to resolved form.
    """
    convert_and_raise_errors(InputERC7730Descriptor.load(input_file), ERC7730InputToResolved())
