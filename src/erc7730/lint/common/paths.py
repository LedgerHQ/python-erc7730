import re
from dataclasses import dataclass
from typing import cast

from erc7730.model.context import EIP712Field, EIP712JsonSchema
from erc7730.model.resolved.display import (
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFormat,
    ResolvedNestedFields,
    TokenAmountParameters,
)

_ARRAY_SUFFIX = "[]"

_INDICE_ARRAY = re.compile(r"\[-?\d+\]")
_SLICE_ARRAY = re.compile(r"\.\[-?\d+:-?\d+\]")


def _append_path(root: str, path: str) -> str:
    return f"{root}.{path}" if root else path


def _cleanup_brackets(token_path: str) -> str:
    without_slices = re.sub(_SLICE_ARRAY, "", token_path)  # remove slicing syntax
    without_indices = re.sub(_INDICE_ARRAY, _ARRAY_SUFFIX, without_slices)  # keep only array syntax
    return without_indices


def compute_eip712_paths(schema: EIP712JsonSchema) -> set[str]:
    """Compute the sets of valid paths for an EIP712 schema."""

    def append_paths(
        path: str, current_type: list[EIP712Field], types: dict[str, list[EIP712Field]], paths: set[str]
    ) -> None:
        for domain in current_type:
            new_path = _append_path(path, domain.name)
            domain_type = domain.type
            if domain_type.endswith(_ARRAY_SUFFIX):
                domain_type = domain_type[: -len(_ARRAY_SUFFIX)]
                new_path += f".{_ARRAY_SUFFIX}"
            if domain_type in types:
                append_paths(new_path, types[domain_type], types, paths)
            else:
                paths.add(new_path)

    if schema.primaryType not in schema.types:
        raise ValueError(f"Invalid schema: primaryType {schema.primaryType} not in types")
    paths: set[str] = set()
    append_paths("", schema.types[schema.primaryType], schema.types, paths)
    return paths


@dataclass(kw_only=True)
class FormatPaths:
    data_paths: set[str]  # References to values in the serialized data
    format_paths: set[str]  # References to values in the format specification file
    container_paths: set[str]  # References to values in the container


def compute_format_paths(format: ResolvedFormat) -> FormatPaths:
    """Compute the sets of paths referred in an ERC7730 Format."""
    paths = FormatPaths(data_paths=set(), format_paths=set(), container_paths=set())

    def add_path(root: str, path: str) -> None:
        path = _cleanup_brackets(path)
        if path.startswith("@."):
            paths.container_paths.add(path[2:])
        elif path.startswith("$."):
            paths.format_paths.add(path[2:])
        elif path.startswith("#."):
            paths.data_paths.add(path[2:])
        else:
            paths.data_paths.add(_append_path(root, path))

    def append_paths(path: str, field: ResolvedField | None) -> None:
        if field is not None:
            match field:
                case ResolvedFieldDescription():
                    add_path(path, field.path)
                    if (
                        (params := field.params)
                        and isinstance(params, TokenAmountParameters)
                        and (token_path := params.tokenPath) is not None
                    ):
                        add_path(path, token_path)
                case ResolvedNestedFields():
                    for nested_field in field.fields:
                        append_paths(_append_path(path, field.path), cast(ResolvedField, nested_field))

    if format.fields is not None:
        for f in format.fields:
            append_paths("", f)
    return paths
