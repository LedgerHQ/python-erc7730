from glob import glob
from pathlib import Path
from typing import Any

import eth_abi
import pytest
from eth_utils import function_abi_to_4byte_selector, get_abi_input_types
from pydantic import BaseModel

from erc7730.common.output import RaisingOutputAdder
from erc7730.common.pydantic import (
    model_from_json_file_with_includes,
    model_to_json_file,
)
from erc7730.convert.calldata.v1.abi import function_to_abi_tree
from erc7730.convert.calldata.v1.path import (
    apply_path,
    convert_data_path,
)
from erc7730.model.abi import Function
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorValueV1,
)
from erc7730.model.input.path import DataPathStr

DATA = Path(__file__).resolve().parent / "data"
UPDATE_REFERENCES = False


class PathEncodingTestCase(BaseModel):
    abi: Function
    path: DataPathStr
    result: CalldataDescriptorValueV1 | None = None
    error: str | None = None


class ValueDecodingTestCase(BaseModel):
    abi: Function
    args: Any
    path: DataPathStr
    result: Any | None = None
    error: str | None = None


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "paths" / "*.json"))), ids=lambda f: Path(f).stem)
def test_convert_paths_by_reference(test_file: str) -> None:
    """
    Given an ABI + an ABI path, build calldata path and check obtained result by reference.
    """
    test_path = Path(test_file)
    test_case = model_from_json_file_with_includes(test_path, PathEncodingTestCase)

    abi_tree = function_to_abi_tree(test_case.abi)

    out = RaisingOutputAdder()

    if (expected_error := test_case.error) is not None:
        with pytest.raises(Exception) as exc_info:
            convert_data_path(test_case.path, abi_tree, out)
        assert expected_error in str(exc_info.value)
    else:
        result = convert_data_path(test_case.path, abi_tree, out)
        if UPDATE_REFERENCES:
            model_to_json_file(test_path, test_case.model_copy(update={"result": result}))
            pytest.fail(f"Reference {test_file} updated, please set UPDATE_REFERENCES back to False")
        elif (expected_result := test_case.result) is not None:
            assert result == expected_result
        else:
            raise Exception("Test case is missing either 'result' or 'error' field")


@pytest.mark.parametrize("test_file", sorted(glob(str(DATA / "values" / "*.json"))), ids=lambda f: Path(f).stem)
def test_decode_values_by_reference(test_file: str) -> None:
    """
    Given an ABI + argument values + an ABI path:
        - encode calldata arguments
        - build calldata path
        - apply calldata path to encoded
        - check decoded value by reference
    """
    test_path = Path(test_file)
    test_case = model_from_json_file_with_includes(test_path, ValueDecodingTestCase)

    abi_dict = test_case.abi.model_dump(mode="json")
    signature = get_abi_input_types(abi_dict)
    selector = function_abi_to_4byte_selector(abi_dict)
    args = eth_abi.encode(signature, test_case.args)
    calldata = (selector + args).hex()

    abi_tree = function_to_abi_tree(test_case.abi)

    if (expected_error := test_case.error) is not None:
        with pytest.raises(Exception) as exc_info:
            path = convert_data_path(test_case.path, abi_tree, RaisingOutputAdder())
            assert path is not None
            apply_path(calldata, path)
        assert expected_error in str(exc_info.value)
    else:
        path = convert_data_path(test_case.path, abi_tree, RaisingOutputAdder())
        assert path is not None
        result = apply_path(calldata, path)
        if UPDATE_REFERENCES:
            model_to_json_file(test_path, test_case.model_copy(update={"result": result}))
            pytest.fail(f"Reference {test_file} updated, please set UPDATE_REFERENCES back to False")
        elif (expected_result := test_case.result) is not None:
            assert result == expected_result
        else:
            raise Exception("Test case is missing either 'result' or 'error' field")
