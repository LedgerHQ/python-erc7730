from pathlib import Path

import pytest

from erc7730.convert.calldata.convert_erc7730_v2_input_to_calldata import (
    erc7730_v2_descriptor_to_calldata_descriptors,
)
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from tests.cases import path_id
from tests.files import ERC7730_DESCRIPTORS, ERC7730_EXPECTED_EMPTY_CALLDATA

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_registry_files(input_file: Path) -> None:
    """
    Test generating calldata descriptors for ERC-7730 registry files (also exercises resolution).
    """
    descriptors = erc7730_v2_descriptor_to_calldata_descriptors(InputERC7730Descriptor.load(input_file))

    if input_file.name in ERC7730_EXPECTED_EMPTY_CALLDATA:
        return

    assert descriptors
    # model_dump_json evaluates every computed TLV .descriptor field, exercising the full TLV encoding
    for descriptor in descriptors:
        assert descriptor.model_dump_json()
