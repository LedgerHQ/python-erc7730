"""
Utilities for computing schema paths from v2 resolved display formats.

These functions extract the set of data paths referenced by a v2 resolved format, which can then be compared against
ABI-derived paths for validation.
"""

from typing import assert_never

from erc7730.model.paths import ContainerPath, DataPath, DescriptorPath
from erc7730.model.paths.path_schemas import FormatPaths, data_path_to_schema_path
from erc7730.model.resolved.v2.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedDateParameters,
    ResolvedEnumParameters,
    ResolvedField,
    ResolvedFieldDescription,
    ResolvedFieldGroup,
    ResolvedFormat,
    ResolvedInteroperableAddressNameParameters,
    ResolvedNftNameParameters,
    ResolvedTokenAmountParameters,
    ResolvedTokenTickerParameters,
    ResolvedUnitParameters,
)
from erc7730.model.resolved.display import ResolvedValue, ResolvedValuePath


def compute_format_schema_paths(fmt: ResolvedFormat) -> FormatPaths:
    """
    Compute the sets of schema paths referred in a v2 ERC7730 Format section.

    :param fmt: resolved v2 $.display.format section
    :return: schema paths used by field formats
    """
    data_paths: set[DataPath] = set()
    container_paths: set[ContainerPath] = set()

    def add_path(path: DescriptorPath | DataPath | ContainerPath | None) -> None:
        if path is None:
            return
        match path:
            case ContainerPath():
                container_paths.add(path)
            case DataPath():
                data_paths.add(data_path_to_schema_path(path))
            case DescriptorPath():
                pass  # descriptor paths are not schema paths

    def add_value(value: ResolvedValue | None) -> None:
        if isinstance(value, ResolvedValuePath):
            add_path(value.path)

    def append_field(field: ResolvedField) -> None:
        match field:
            case ResolvedFieldDescription():
                # Add the field's own path
                if field.path is not None:
                    add_path(field.path)

                # Add paths from parameters
                match field.params:
                    case None:
                        pass
                    case ResolvedAddressNameParameters():
                        pass
                    case ResolvedInteroperableAddressNameParameters():
                        pass
                    case ResolvedCallDataParameters():
                        add_value(field.params.callee)
                        add_value(field.params.selector)
                        add_value(field.params.amount)
                        add_value(field.params.spender)
                    case ResolvedTokenAmountParameters():
                        if isinstance(field.params.token, ResolvedValuePath):
                            add_path(field.params.token.path)
                        add_path(field.params.chainIdPath)
                    case ResolvedTokenTickerParameters():
                        add_path(field.params.chainIdPath)
                    case ResolvedNftNameParameters():
                        add_value(field.params.collection)
                    case ResolvedDateParameters():
                        pass
                    case ResolvedUnitParameters():
                        pass
                    case ResolvedEnumParameters():
                        pass
                    case _:
                        assert_never(field.params)
            case ResolvedFieldGroup():
                for sub_field in field.fields:
                    append_field(sub_field)
            case _:
                assert_never(field)

    for field in fmt.fields:
        append_field(field)

    return FormatPaths(data_paths=data_paths, container_paths=container_paths)
