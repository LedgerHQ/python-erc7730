from pathlib import Path

import pytest

from erc7730.convert.convert import convert_and_raise_errors
from erc7730.convert.resolved.convert_erc7730_input_to_resolved import ERC7730InputToResolved
from erc7730.model.input.descriptor import InputERC7730Descriptor
from erc7730.model.resolved.descriptor import ResolvedERC7730Descriptor
from tests.assertions import assert_model_json_equals
from tests.cases import TestCase, case_id, path_id
from tests.files import ERC7730_DESCRIPTORS
from tests.skip import single_or_skip

DATA = Path(__file__).resolve().parent / "data"
UPDATE_REFERENCES = False


@pytest.mark.parametrize("input_file", ERC7730_DESCRIPTORS, ids=path_id)
def test_registry_files(input_file: Path) -> None:
    """
    Test converting ERC-7730 registry files from input to resolved form.
    """

    # TODO: these descriptors use literal constants instead of token paths, which is not supported yet
    if input_file.name in {"calldata-OssifiableProxy.json", "calldata-wstETH.json", "calldata-usdt.json"}:
        pytest.skip("Descriptor uses literal constants instead of token paths, which is not supported yet")

    convert_and_raise_errors(InputERC7730Descriptor.load(input_file), ERC7730InputToResolved())


@pytest.mark.parametrize(
    "testcase",
    [
        TestCase(
            id="minimal_eip712",
            label="minimal EIP-712 descriptor",
            description="most minimal possible EIP-712 file: all optional fields unset, resolved form is identical to "
            "input form",
        ),
        TestCase(
            id="minimal_contract",
            label="minimal contract descriptor",
            description="most minimal possible contract file: all optional fields unset, resolved form is identical to "
            "input form",
        ),
        TestCase(
            id="format_raw",
            label="field format - using raw format",
            description="using raw format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_address_name",
            label="field format - using address name format",
            description="using address name format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_calldata",
            label="field format - using calldata format",
            description="using calldata format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_amount",
            label="field format - using amount format",
            description="using amount format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_token_amount",
            label="field format - using token amount format",
            description="using token amount format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_nft_name",
            label="field format - using NFT name amount format",
            description="using NFT name amount format, with parameter variants, resolved form is identical to input "
            "form",
        ),
        TestCase(
            id="format_date",
            label="field format - using date format",
            description="using date format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_duration",
            label="field format - using duration format",
            description="using duration format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_unit",
            label="field format - using unit format",
            description="using unit format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_enum",
            label="field format - using enum format",
            description="using enum format, with parameter variants, resolved form is identical to input form",
        ),
        TestCase(
            id="format_raw_using_constants",
            label="field format - using raw format with references to constants",
            description="using raw format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_address_name_using_constants",
            label="field format - using address name format with references to constants",
            description="using address name format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_calldata_using_constants",
            label="field format - using calldata format with references to constants",
            description="using calldata format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_amount_using_constants",
            label="field format - using amount format with references to constants",
            description="using amount format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_token_amount_using_constants",
            label="field format - using token amount format with references to constants",
            description="using token amount format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_nft_name_using_constants",
            label="field format - using NFT name amount format with references to constants",
            description="using NFT name amount format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_date_using_constants",
            label="field format - using date format with references to constants",
            description="using date format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_duration_using_constants",
            label="field format - using duration format with references to constants",
            description="using duration format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_unit_using_constants",
            label="field format - using unit format with references to constants",
            description="using unit format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="format_enum_using_constants",
            label="field format - using enum format with references to constants",
            description="using enum format, with parameter variants and $.context/$.metadata constants",
        ),
        TestCase(
            id="definition_format_raw",
            label="display definition / reference - using raw format",
            description="most minimal possible use of a display definition + reference, using raw format",
        ),
        TestCase(
            id="definition_format_address_name",
            label="display definition / reference - using address name format",
            description="most minimal possible use of a display definition + reference, using address name format",
        ),
        TestCase(
            id="definition_format_calldata",
            label="display definition / reference - using calldata format",
            description="most minimal possible use of a display definition + reference, using calldata format",
        ),
        TestCase(
            id="definition_format_amount",
            label="display definition / reference - using amount format",
            description="most minimal possible use of a display definition + reference, using amount format",
        ),
        TestCase(
            id="definition_format_token_amount",
            label="display definition / reference - using token amount format",
            description="most minimal possible use of a display definition + reference, using token amount format",
        ),
        TestCase(
            id="definition_format_nft_name",
            label="display definition / reference - using NFT name format",
            description="most minimal possible use of a display definition + reference, using NFT name format",
        ),
        TestCase(
            id="definition_format_date",
            label="display definition / reference - using date format",
            description="most minimal possible use of a display definition + reference, using date format",
        ),
        TestCase(
            id="definition_format_duration",
            label="display definition / reference - using duration format",
            description="most minimal possible use of a display definition + reference, using duration format",
        ),
        TestCase(
            id="definition_format_unit",
            label="display definition / reference - using unit format",
            description="most minimal possible use of a display definition + reference, using unit format",
        ),
        TestCase(
            id="definition_format_enum",
            label="display definition / reference - using enum format",
            description="most minimal possible use of a display definition + reference, using enum format",
        ),
        TestCase(
            id="definition_override_label",
            label="display definition / reference - using label override",
            description="use of a display definition, with label overridden on the field",
        ),
        TestCase(
            id="definition_override_params",
            label="display definition / reference - using params override",
            description="use of a display definition, with parameters overridden on the field",
        ),
        TestCase(
            id="definition_using_constants",
            label="display definition / reference - using constants override",
            description="use of a display definition, using $.context/$.metadata constants",
        ),
        TestCase(
            id="definition_invalid_container_path",
            label="display definition / reference - using a container path",
            description="use of a reference to a display definition with a container path",
            error="descriptor path referencing a value in the descriptor document using jsonpath syntax, such as",
        ),
        TestCase(
            id="definition_invalid_data_path",
            label="display definition / reference - using a data path",
            description="use of a reference to a display definition with a data path",
            error="descriptor path referencing a value in the descriptor document using jsonpath syntax, such as",
        ),
        TestCase(
            id="definition_invalid_path_does_not_exist",
            label="display definition / reference - using a path that does not exist",
            description="use of a reference to a display definition that does not exist",
            error="""Display definition "does_not_exist" does not exist, valid ones are: test_definition.""",
        ),
        TestCase(
            id="definition_invalid_path_not_a_field",
            label="display definition / reference - using a path that is not a field",
            description="use of a reference path that is not a simple field reference",
            error="References to display field definitions are restricted to fields immediately under "
            "$.display.definitions",
        ),
        TestCase(
            id="definition_invalid_path_outside_display_definitions",
            label="display definition / reference - using a path outside of $.display.definitions",
            description="use of a reference to a display outside of allowed root path $.display.definitions",
            error="References to display field definitions are restricted to $.display.definitions",
        ),
        TestCase(
            id="definition_invalid_nested_path",
            label="display definition / reference - using a path nested under $.display.definitions",
            description="use of a valid reference to a display definition nested too deep under $.display.definitions",
            error="References to display field definitions are restricted to fields immediately under "
            "$.display.definitions",
        ),
        TestCase(
            id="definition_invalid_parameter_overrides",
            label="display definition / reference - using invalid parameter overrides",
            description="use of a valid reference to a valid display definition, with invalid overrides",
            error="Extra inputs are not permitted",
        ),
        TestCase(
            id="nested_fields_eip712_array",
            label="nested fields - array parameter (EIP-712 descriptor)",
            description="use of nested fields on an array parameter (EIP-712 descriptor)",
        ),
        TestCase(
            id="nested_fields_eip712_struct",
            label="nested fields - struct parameter (EIP-712 descriptor)",
            description="use of nested fields on a struct parameter (EIP-712 descriptor)",
        ),
        TestCase(
            id="unsupported_using_literal_values",
            label="unsupported: using literal value instead of data path",
            description="using a literal value where a data path is expected",
            error="It seems you are trying to use a constant address value instead",
        ),
        TestCase(
            id="unsupported_using_literal_values_as_constants",
            label="unsupported: using literal value instead of data path",
            description="using a literal value where a data path is expected, defined in constants section",
            error="It seems you are trying to use a constant address value instead",
        ),
    ],
    ids=case_id,
)
def test_by_reference(testcase: TestCase) -> None:
    """
    Test converting ERC-7730 descriptor files from input to resolved form, and compare against reference files.
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
