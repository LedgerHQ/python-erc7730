import pytest
from pydantic import TypeAdapter, ValidationError

from erc7730.model.input.path import ContainerPathStr, DataPathStr, DescriptorPathStr
from erc7730.model.paths import (
    Array,
    ArrayElement,
    ArraySlice,
    ContainerField,
    ContainerPath,
    DataPath,
    DescriptorPath,
    Field,
)
from erc7730.model.paths.path_parser import to_path
from erc7730.model.resolved.path import ResolvedPath
from tests.assertions import assert_json_str_equals


def _test_valid_input_path(string: str, obj: DescriptorPathStr | DataPathStr | ContainerPathStr, json: str) -> None:
    assert_json_str_equals(json, obj.to_json_string())
    assert to_path(string) == obj
    assert TypeAdapter(DescriptorPathStr | DataPathStr | ContainerPathStr).validate_json(f'"{string}"') == obj
    assert TypeAdapter(DescriptorPath | DataPath | ContainerPath).validate_json(json) == obj
    assert str(obj) == string


def _test_valid_resolved_path(string: str, obj: ResolvedPath, json: str) -> None:
    assert_json_str_equals(json, obj.to_json_string())
    assert to_path(string) == obj
    assert TypeAdapter(ResolvedPath).validate_json(json) == obj
    assert str(obj) == string


def test_valid_input_container_path() -> None:
    _test_valid_input_path(
        string="@.to",
        obj=ContainerPath(field=ContainerField.TO),
        json="""{ "type": "container", "field": "to" }""",
    )


def test_valid_input_data_path_absolute() -> None:
    _test_valid_input_path(
        string="#.params.[].[-2].[1:5].[:5].[5:].amountIn",
        obj=DataPath(
            absolute=True,
            elements=[
                Field(identifier="params"),
                Array(),
                ArrayElement(index=-2),
                ArraySlice(start=1, end=5),
                ArraySlice(start=None, end=5),
                ArraySlice(start=5, end=None),
                Field(identifier="amountIn"),
            ],
        ),
        json="""
            {
              "type": "data",
              "absolute": true,
              "elements": [
                { "type": "field", "identifier": "params" },
                { "type": "array" },
                { "type": "array_element", "index": -2 },
                { "type": "array_slice", "start": 1, "end": 5 },
                { "type": "array_slice", "end": 5 },
                { "type": "array_slice", "start": 5 },
                { "type": "field", "identifier": "amountIn" }
              ]
            }
        """,
    )


def test_valid_input_data_path_relative() -> None:
    _test_valid_input_path(
        string="params.[].[-2].[1:5].amountIn",
        obj=DataPath(
            absolute=False,
            elements=[
                Field(identifier="params"),
                Array(),
                ArrayElement(index=-2),
                ArraySlice(start=1, end=5),
                Field(identifier="amountIn"),
            ],
        ),
        json="""
            {
              "type": "data",
              "absolute": false,
              "elements": [
                { "type": "field", "identifier": "params" },
                { "type": "array" },
                { "type": "array_element", "index": -2 },
                { "type": "array_slice", "start": 1, "end": 5 },
                { "type": "field", "identifier": "amountIn" }
              ]
            }
        """,
    )


def test_valid_input_descriptor_path() -> None:
    _test_valid_input_path(
        string="$.params.[-2].[0].amountIn",
        obj=DescriptorPath(
            elements=[
                Field(identifier="params"),
                ArrayElement(index=-2),
                ArrayElement(index=0),
                Field(identifier="amountIn"),
            ]
        ),
        json="""
            {
              "type": "descriptor",
              "elements": [
                { "type": "field", "identifier": "params" },
                { "type": "array_element", "index": -2 },
                { "type": "array_element", "index": 0 },
                { "type": "field", "identifier": "amountIn" }
              ]
            }
        """,
    )


def test_valid_resolved_container_path() -> None:
    _test_valid_resolved_path(
        string="@.to",
        obj=ContainerPath(field=ContainerField.TO),
        json="""{ "type": "container", "field": "to" }""",
    )


def test_valid_resolved_data_path() -> None:
    _test_valid_resolved_path(
        string="#.params.[].[-2].[1:5].amountIn",
        obj=DataPath(
            absolute=True,
            elements=[
                Field(identifier="params"),
                Array(),
                ArrayElement(index=-2),
                ArraySlice(start=1, end=5),
                Field(identifier="amountIn"),
            ],
        ),
        json="""
            {
              "type": "data",
              "absolute": true,
              "elements": [
                { "type": "field", "identifier": "params" },
                { "type": "array" },
                { "type": "array_element", "index": -2 },
                { "type": "array_slice", "start": 1, "end": 5 },
                { "type": "field", "identifier": "amountIn" }
              ]
            }
        """,
    )


def test_invalid_container_value_unknown() -> None:
    with pytest.raises(ValueError) as e:
        to_path("@.foo")
    message = str(e.value)
    assert "Invalid path" in message
    assert "@.foo" in message
    assert "Expected one of" in message


def test_invalid_container_path_empty_component() -> None:
    with pytest.raises(ValueError) as e:
        to_path("@..foo")
    message = str(e.value)
    assert "Invalid path" in message
    assert "@..foo" in message
    assert "Expected one of" in message


def test_invalid_field_identifier_not_ascii() -> None:
    with pytest.raises(ValueError) as e:
        to_path("#.👿")
    message = str(e.value)
    assert "Invalid path" in message
    assert "#.👿" in message
    assert "Expected one of" in message


def test_invalid_array_element_index_not_a_number() -> None:
    with pytest.raises(ValueError) as e:
        to_path("#.[foo]")
    message = str(e.value)
    assert "Invalid path" in message
    assert "#.[foo]" in message
    assert "Expected one of" in message


def test_invalid_array_element_index_out_of_bounds() -> None:
    with pytest.raises(ValueError) as e:
        to_path("#.[65536]")
    message = str(e.value)
    assert "Invalid path" in message
    assert "#.[65536]" in message
    assert "Input should be less than or equal" in message


def test_invalid_array_slice_inverted() -> None:
    with pytest.raises(ValueError) as e:
        to_path("#.[1:0]")
    message = str(e.value)
    assert "Invalid path" in message
    assert "#.[1:0]" in message
    assert "Array slice start index must be strictly lower than end index" in message


def test_invalid_array_slice_used_in_descriptor_path() -> None:
    with pytest.raises(ValueError) as e:
        to_path("$.[1:0]")
    message = str(e.value)
    assert "Invalid path" in message
    assert "$.[1:0]" in message
    assert "Expected one of" in message


def test_invalid_array_used_in_descriptor_path() -> None:
    with pytest.raises(ValueError) as e:
        to_path("$.[]")
    message = str(e.value)
    assert "Invalid path" in message
    assert "$.[]" in message
    assert "Expected one of" in message


def test_invalid_relative_resolved_data_path() -> None:
    with pytest.raises(ValidationError) as e:
        TypeAdapter(ResolvedPath).validate_python(to_path("params.[].[-2].[1:5].amountIn"))
    message = str(e.value)
    assert "A resolved data path must be absolute" in message
