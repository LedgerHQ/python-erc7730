from dataclasses import dataclass
from typing import assert_never

from eip712.model.schema import EIP712SchemaField

from erc7730.model.abi import Component, Function, InputOutput
from erc7730.model.context import EIP712JsonSchema
from erc7730.model.paths import (
    ROOT_DATA_PATH,
    Array,
    ArrayElement,
    ArraySlice,
    ContainerPath,
    DataPath,
    DataPathElement,
    Field,
)
from erc7730.model.paths.path_ops import data_path_append
from erc7730.model.resolved.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedDateParameters,
    ResolvedEnumParameters,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFormat,
    ResolvedNestedFields,
    ResolvedNftNameParameters,
    ResolvedTokenAmountParameters,
    ResolvedUnitParameters,
)
from erc7730.model.resolved.path import ResolvedPath


@dataclass(kw_only=True, frozen=True)
class FormatPaths:
    data_paths: set[DataPath]  # References to values in the serialized data
    container_paths: set[ContainerPath]  # References to values in the container


def compute_eip712_schema_paths(schema: EIP712JsonSchema) -> set[DataPath]:
    """
    Compute the sets of valid schema paths for an EIP-712 schema.

    :param schema: EIP-712 schema
    :return: valid schema paths
    """

    if (primary_type := schema.types.get(schema.primaryType)) is None:
        raise ValueError(f"Invalid schema: primaryType {schema.primaryType} not in types")

    paths: set[DataPath] = set()

    def append_paths(path: DataPath, current_type: list[EIP712SchemaField]) -> None:
        for field in current_type:
            sub_path = data_path_append(path, Field(identifier=field.name))
            paths.add(sub_path)
            if (field_type := field.type.rstrip("[]")) != field.type:
                sub_path = data_path_append(path, Array())
            else:
                field_type = field.type
            if (target_type := schema.types.get(field_type)) is not None:
                append_paths(sub_path, target_type)

    append_paths(ROOT_DATA_PATH, primary_type)

    return paths


def compute_abi_schema_paths(abi: Function) -> set[DataPath]:
    """
    Compute the sets of valid schema paths for an ABI function.

    :param abi: Solidity ABI function
    :return: valid schema paths
    """
    paths: set[DataPath] = set()

    def append_paths(path: DataPath, params: list[InputOutput] | list[Component] | None) -> None:
        if not params:
            return None
        for param in params:
            sub_path = data_path_append(path, Field(identifier=param.name))

            param_type = param.type
            if param_type.rstrip("[]") != param_type:
                sub_path = data_path_append(sub_path, Array())
                paths.add(sub_path)

            if param.components:
                append_paths(sub_path, param.components)  # type: ignore
            else:
                paths.add(sub_path)

    append_paths(ROOT_DATA_PATH, abi.inputs)

    return paths


def compute_format_schema_paths(format: ResolvedFormat) -> FormatPaths:
    """
    Compute the sets of schema paths referred in an ERC7730 Format section.

    :param format: resolved $.display.format section
    :return: schema paths used by field formats
    """
    data_paths: set[DataPath] = set()  # references to values in the serialized data
    container_paths: set[ContainerPath] = set()  # references to values in the container

    if format.fields is not None:

        def add_path(path: ResolvedPath | None) -> None:
            match path:
                case None:
                    pass
                case ContainerPath():
                    container_paths.add(path)
                case DataPath():
                    data_paths.add(data_path_to_schema_path(path))
                case _:
                    assert_never(path)

        def append_paths(field: ResolvedField) -> None:
            match field:
                case ResolvedFieldDescription():
                    add_path(field.path)
                    match field.params:
                        case None:
                            pass
                        case ResolvedAddressNameParameters():
                            pass
                        case ResolvedCallDataParameters(calleePath=callee_path):
                            add_path(callee_path)
                        case ResolvedTokenAmountParameters(tokenPath=token_path):
                            add_path(token_path)
                        case ResolvedNftNameParameters(collectionPath=collection_path):
                            add_path(collection_path)
                        case ResolvedDateParameters():
                            pass
                        case ResolvedUnitParameters():
                            pass
                        case ResolvedEnumParameters():
                            pass
                        case _:
                            assert_never(field.params)
                case ResolvedNestedFields():
                    for nested_field in field.fields:
                        append_paths(nested_field)
                case _:
                    assert_never(field)

        for field in format.fields:
            append_paths(field)

    return FormatPaths(data_paths=data_paths, container_paths=container_paths)


def data_path_to_schema_path(path: DataPath) -> DataPath:
    """
    Convert a data path to a schema path.

    Example: #.foo.[].[-2].[1:5].bar -> #.foo.[].[].[].bar

    :param path: data path
    :return: schema path
    """

    def to_schema(element: DataPathElement) -> DataPathElement:
        match element:
            case Field() as f:
                return f
            case Array() | ArrayElement() | ArraySlice():
                return Array()
            case _:
                assert_never(element)

    return path.model_copy(update={"elements": [to_schema(e) for e in path.elements]})
