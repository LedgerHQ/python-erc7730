import re
from dataclasses import dataclass

from erc7730.model.abi import Component, Function, InputOutput
from erc7730.model.context import EIP712Field, EIP712JsonSchema
from erc7730.model.paths import EMPTY_DATA_PATH, Array, ContainerPath, DataPath, Field
from erc7730.model.paths.path_ops import append_data_path
from erc7730.model.resolved.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFormat,
    ResolvedNestedFields,
    ResolvedTokenAmountParameters,
)
from erc7730.model.resolved.path import ResolvedPath

_ARRAY_SUFFIX = "[]"
_INDICE_ARRAY = re.compile(r"\[-?\d+\]")
_SLICE_ARRAY = re.compile(r"\.\[-?\d+:-?\d+\]")


@dataclass(kw_only=True, frozen=True)
class FormatPaths:
    data_paths: set[DataPath]  # References to values in the serialized data
    container_paths: set[ContainerPath]  # References to values in the container


def compute_format_paths(format: ResolvedFormat) -> FormatPaths:
    """Compute the sets of paths referred in an ERC7730 Format."""
    data_paths: set[DataPath]  # References to values in the serialized data
    container_paths: set[ContainerPath]  # References to values in the container

    if format.fields is not None:

        def cleanup_brackets(token_path: ResolvedPath) -> ResolvedPath:
            without_slices = re.sub(_SLICE_ARRAY, "", token_path)  # remove slicing syntax
            without_indices = re.sub(_INDICE_ARRAY, _ARRAY_SUFFIX, without_slices)  # keep only array syntax
            return without_indices

        def add_path(path: ResolvedPath) -> None:
            match cleanup_brackets(path):
                case ContainerPath():
                    container_paths.add(path)
                case DataPath():
                    data_paths.add(path)

        def append_paths(field: ResolvedField) -> None:
            match field:
                case ResolvedFieldDescription():
                    add_path(field.path)
                    if (
                        (params := field.params)
                        and isinstance(params, ResolvedTokenAmountParameters)
                        and (token_path := params.tokenPath) is not None
                    ):
                        add_path(token_path)
                case ResolvedNestedFields():
                    for nested_field in field.fields:
                        append_paths(nested_field)

        for f in format.fields:
            append_paths(f)

    return FormatPaths(data_paths=data_paths, container_paths=container_paths)


def compute_eip712_paths(schema: EIP712JsonSchema) -> set[DataPath]:
    """Compute the sets of valid paths for an EIP712 schema."""

    if (primary_type := schema.types.get(schema.primaryType)) is None:
        raise ValueError(f"Invalid schema: primaryType {schema.primaryType} not in types")

    paths: set[DataPath] = set()

    def append_paths(path: DataPath, current_type: list[EIP712Field]) -> None:
        for field in current_type:
            new_path = append_data_path(path, Field(identifier=field.name))
            field_type = field.type
            if field_type.endswith(_ARRAY_SUFFIX):
                field_type = field_type[: -len(_ARRAY_SUFFIX)]
                new_path = append_data_path(path, Array())
            if (target_type := schema.types.get(field_type)) is not None:
                append_paths(new_path, target_type)
            else:
                paths.add(new_path)

    append_paths(EMPTY_DATA_PATH, primary_type)

    return paths


def compute_abi_paths(abi: Function) -> set[DataPath]:
    """Compute the sets of valid paths for a Function."""

    paths: set[DataPath] = set()

    def append_paths(path: DataPath, params: list[InputOutput] | list[Component] | None) -> None:
        if params:
            for param in params:
                param_name = param.name + ".[]" if param.type.endswith("[]") else param.name
                param_path = append_data_path(path, Field(identifier=param_name))
                if param.components:
                    append_paths(param_path, param.components)  # type: ignore
                else:
                    paths.add(param_path)

    append_paths(EMPTY_DATA_PATH, abi.inputs)

    return paths
