from pathlib import Path

import pytest

from erc7730.common.output import ExceptionsToOutput, SetOutputAdder
from erc7730.model.input.descriptor import InputERC7730Descriptor
from tests.cases import TestCase, case_id

DATA = Path(__file__).resolve().parent / "data"


@pytest.mark.parametrize(
    "testcase",
    [
        TestCase(
            id="format_token_amount_native_currency_address_using_data_path",
            label="using a data path where an address value is expected",
            description="using a literal value where a data path is expected",
            error="expected a 20 bytes, hexadecimal Ethereum address",
        ),
    ],
    ids=case_id,
)
def test_errors_by_reference(testcase: TestCase) -> None:
    """
    Test loading and validating and erroneous ERC-7730 descriptor files, and compare against expected errors.
    """
    input_descriptor_path = DATA / "errors" / f"{testcase.id}.json"
    if (expected_error := testcase.error) is None:
        pytest.fail("Testcase must have an expected error")
    out = SetOutputAdder()
    with ExceptionsToOutput(out):
        InputERC7730Descriptor.load(input_descriptor_path)
    messages = {output.message for output in out.outputs}
    assert any(expected_error in message for message in messages), "Expected error not found in:\n" + "\n".join(
        messages
    )
