from pathlib import Path

import pytest

from erc7730.convert.convert import convert_and_raise_errors
from erc7730.convert.resolved.v2.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.v2.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.v2.descriptor import ResolvedERC7730Descriptor
from tests.assertions import assert_model_json_equals
from tests.cases import TestCase, case_id
from tests.skip import single_or_skip

DATA = Path(__file__).resolve().parent / "data"
UPDATE_REFERENCES = False


@pytest.mark.parametrize(
    "testcase",
    [
        TestCase(
            id="minimal_eip712_v2",
            label="minimal EIP-712 v2 descriptor",
            description="most minimal possible EIP-712 v2 file: all optional fields unset, resolved form is identical "
            "to input form",
        ),
        TestCase(
            id="minimal_contract_v2",
            label="minimal contract v2 descriptor",
            description="most minimal possible contract v2 file: all optional fields unset, resolved form is identical "
            "to input form",
        ),
        TestCase(
            id="deprecated_abi_ignored",
            label="deprecated ABI field ignored",
            description="contract descriptor with deprecated ABI field is ignored during conversion to resolved form",
        ),
        TestCase(
            id="deprecated_schemas_ignored",
            label="deprecated schemas field ignored",
            description="EIP-712 descriptor with deprecated schemas field is ignored during conversion to resolved "
            "form",
        ),
        TestCase(
            id="format_token_ticker",
            label="field format - using token ticker format",
            description="using token ticker format with chainId parameter variants",
        ),
        TestCase(
            id="format_interoperable_address_name",
            label="field format - using interoperable address name format",
            description="using interoperable address name format with parameter variants",
        ),
        TestCase(
            id="format_chain_id",
            label="field format - using chain ID format",
            description="using chain ID format to display chain name",
        ),
        TestCase(
            id="field_with_encryption",
            label="field with encryption parameters",
            description="using encryption parameters for encrypted value display",
        ),
        TestCase(
            id="field_definition_with_encryption",
            label="field definition with encryption parameters",
            description="using encryption parameters in display definitions and resolving via $ref",
        ),
        TestCase(
            id="field_with_visibility_simple",
            label="field with simple visibility rule",
            description="using simple string visibility rule",
        ),
        TestCase(
            id="field_with_visibility_conditions",
            label="field with visibility conditions",
            description="using visibility conditions with ifNotIn/mustBe",
        ),
        TestCase(
            id="field_with_separator",
            label="field with separator",
            description="using separator with {index} interpolation",
        ),
        TestCase(
            id="field_group_basic",
            label="field group - basic usage",
            description="using field group on array with basic configuration",
        ),
        TestCase(
            id="field_group_with_iteration",
            label="field group - with iteration strategy",
            description="using field group with sequential/bundled iteration",
        ),
        TestCase(
            id="field_group_with_label",
            label="field group - with label",
            description="using field group with label for array display",
        ),
        TestCase(
            id="format_with_interpolated_intent",
            label="format with interpolated intent",
            description="using interpolatedIntent with {path} syntax",
        ),
        TestCase(
            id="metadata_with_maps",
            label="metadata with maps",
            description="using maps in metadata section",
        ),
        TestCase(
            id="metadata_with_contract_name",
            label="metadata with contract name",
            description="using contractName field in metadata",
        ),
        TestCase(
            id="token_amount_with_chainid",
            label="token amount with chainId",
            description="using token amount format with chainId parameter for cross-chain tokens",
        ),
        TestCase(
            id="calldata_with_extended_params",
            label="calldata with extended parameters",
            description="using calldata format with chainId, amount, and spender parameters",
        ),
        TestCase(
            id="nft_name_with_collection_path",
            label="nft name with collection path",
            description="using nft name format with collectionPath resolved as ResolvedValue path",
        ),
    ],
    ids=case_id,
)
def test_by_reference(testcase: TestCase) -> None:
    """
    Test converting ERC-7730 v2 descriptor files from input to resolved form, and compare against reference files.
    """
    input_descriptor_path = DATA / f"{testcase.id}_input.json"
    resolved_descriptor_path = DATA / f"{testcase.id}_resolved.json"
    if (expected_error := testcase.error) is not None:
        with pytest.raises(Exception) as exc_info:
            input_descriptor = InputERC7730Descriptor.load(input_descriptor_path)
            convert_and_raise_errors(input_descriptor, ERC7730InputToResolved())
        assert expected_error in str(exc_info.value)
    else:
        input_descriptor = InputERC7730Descriptor.load(input_descriptor_path)
        actual_descriptor: ResolvedERC7730Descriptor = single_or_skip(
            convert_and_raise_errors(input_descriptor, ERC7730InputToResolved())
        )
        if UPDATE_REFERENCES:
            actual_descriptor.save(resolved_descriptor_path)
            pytest.fail(f"Reference {resolved_descriptor_path} updated, please set UPDATE_REFERENCES back to False")
        else:
            expected_descriptor = ResolvedERC7730Descriptor.load(resolved_descriptor_path)
            assert_model_json_equals(expected_descriptor, actual_descriptor)
