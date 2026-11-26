"""
Conversion of ERC-7730 v2 EIP-712 data paths to calldata descriptor EIP712_PATH binary paths.

Unlike DATA_PATH (which navigates serialized calldata by byte offsets using the ABI), EIP712_PATH navigates the
EIP-712 value tree by struct field index and array slices, using the reconstructed schema. Referred to as
"EIP712 v2" in the Ethereum app specifications.
"""

from erc7730.common.output import OutputAdder
from erc7730.convert.calldata.v1.eip712_schema import ParsedSolidityType, parse_solidity_type
from erc7730.model.calldata.v1.eip712 import CalldataDescriptorEIP712SolType
from erc7730.model.calldata.v1.value import (
    MAX_EIP712_PATH_ELEMENTS,
    CalldataDescriptorEIP712PathElementArraySliceV1,
    CalldataDescriptorEIP712PathElementLeafSliceV1,
    CalldataDescriptorEIP712PathElementStructFieldV1,
    CalldataDescriptorEIP712PathElementV1,
    CalldataDescriptorEIP712PathV1,
    CalldataDescriptorTypeFamily,
    CalldataDescriptorValuePathV1,
)
from erc7730.model.paths import (
    Array,
    ArrayElement,
    ArraySlice,
    DataPath,
    Field,
)

_SOL_TYPE_TO_FAMILY: dict[CalldataDescriptorEIP712SolType, CalldataDescriptorTypeFamily] = {
    CalldataDescriptorEIP712SolType.UINT: CalldataDescriptorTypeFamily.UINT,
    CalldataDescriptorEIP712SolType.INT: CalldataDescriptorTypeFamily.INT,
    CalldataDescriptorEIP712SolType.ADDRESS: CalldataDescriptorTypeFamily.ADDRESS,
    CalldataDescriptorEIP712SolType.BOOL: CalldataDescriptorTypeFamily.BOOL,
    CalldataDescriptorEIP712SolType.STRING: CalldataDescriptorTypeFamily.STRING,
    CalldataDescriptorEIP712SolType.BYTES_FIX: CalldataDescriptorTypeFamily.BYTES,
    CalldataDescriptorEIP712SolType.BYTES_DYN: CalldataDescriptorTypeFamily.BYTES,
}


# leaf types a leaf slice applies to
_MIN_BOUND = -32768
_MAX_BOUND = 32767
_MAX_FIELD_INDEX = 255
_MAX_SELECTED_VALUES = 16

_SLICEABLE_LEAVES = (
    CalldataDescriptorEIP712SolType.BYTES_FIX,
    CalldataDescriptorEIP712SolType.BYTES_DYN,
    CalldataDescriptorEIP712SolType.STRING,
)


def _unrepresentable_bound(*bounds: int | None) -> int | None:
    """First bound the device cannot represent (signed 16 bits), if any."""
    return next((bound for bound in bounds if bound is not None and not _MIN_BOUND <= bound <= _MAX_BOUND), None)


def _resolve_bound(bound: int | None, size: int, default: int) -> int:
    """Resolve a bound against the size of what it slices: a negative bound counts back from the end."""
    if bound is None:
        return default
    return bound + size if bound < 0 else bound


def _is_inside(start: int | None, end: int | None, size: int) -> bool:
    """Whether a slice reaches neither before nor past what it slices, an empty selection being valid."""
    return _resolve_bound(start, size, 0) >= 0 and 0 <= _resolve_bound(end, size, size) <= size


def _current_dimension(parsed: ParsedSolidityType | None, remaining_dims: int) -> int | None:
    """Size of the array dimension a selector applies to (outermost first), None when it is dynamic."""
    return parsed.array_dimensions[remaining_dims - 1] if parsed is not None else None


def _is_empty_leaf_slice(start: int | None, end: int | None) -> bool:
    """Whether a leaf slice selects no byte whatever the length of the leaf (which the device refuses)."""
    first = 0 if start is None else start
    return end is not None and (end == 0 or ((first < 0) == (end < 0) and end <= first))


def _selected_count(dimension: int | None, start: int | None, end: int | None) -> int:
    """Number of elements of an array dimension a slice selects at the least, whatever the array it is applied to."""
    if dimension is not None:
        return max(_resolve_bound(end, dimension, dimension) - _resolve_bound(start, dimension, 0), 0)
    if (start is None or start >= 0) and end is not None and end >= 0:
        return max(end - (start or 0), 0)
    return 0


def _leaf_type_family_size(parsed: ParsedSolidityType) -> tuple[CalldataDescriptorTypeFamily, int | None]:
    """Determine the VALUE type family and size (in bytes) from the leaf Solidity type."""
    match parsed.sol_type:
        case CalldataDescriptorEIP712SolType.ADDRESS:
            return CalldataDescriptorTypeFamily.ADDRESS, 20
        case CalldataDescriptorEIP712SolType.BOOL:
            return CalldataDescriptorTypeFamily.BOOL, 1
        case CalldataDescriptorEIP712SolType.UINT | CalldataDescriptorEIP712SolType.INT:
            return _SOL_TYPE_TO_FAMILY[parsed.sol_type], parsed.type_size
        case CalldataDescriptorEIP712SolType.BYTES_FIX:
            return CalldataDescriptorTypeFamily.BYTES, parsed.type_size
        case CalldataDescriptorEIP712SolType.BYTES_DYN | CalldataDescriptorEIP712SolType.STRING:
            return _SOL_TYPE_TO_FAMILY[parsed.sol_type], None
        case _:
            return CalldataDescriptorTypeFamily.BYTES, None


def convert_eip712_data_path(
    data_path: DataPath,
    primary_type: str,
    types: dict[str, list[tuple[str, str]]],
    out: OutputAdder,
) -> CalldataDescriptorValuePathV1 | None:
    """
    Convert an EIP-712 data path to a calldata descriptor EIP712_PATH value.

    :param data_path: resolved data path (referencing the EIP-712 value tree)
    :param primary_type: the message primary type (root struct the path starts from)
    :param types: struct name -> ordered list of (type string, field name)
    :param out: error handler
    :return: calldata value, or None on error
    """
    elements: list[CalldataDescriptorEIP712PathElementV1] = []
    current_struct: str = primary_type
    current_parsed: ParsedSolidityType | None = None
    remaining_dims = 0
    leaf_sliced = False
    slice_width: int | None = None
    # values the path selects at the least, the device refuses a path that necessarily selects more than it holds
    selected = 1

    last_index = len(data_path.elements) - 1
    for position, element in enumerate(data_path.elements):
        match element:
            case Field(identifier=name):
                if current_parsed is not None:
                    if remaining_dims != 0:
                        return out.error(
                            title="Invalid EIP-712 path",
                            message=f'Array of "{current_struct}" not fully indexed before descending into "{name}".',
                        )
                    if current_parsed.sol_type != CalldataDescriptorEIP712SolType.STRUCT or (
                        current_parsed.struct_name is None
                    ):
                        return out.error(
                            title="Invalid EIP-712 path",
                            message=f'Cannot descend into field "{name}" of a non-struct type.',
                        )
                    current_struct = current_parsed.struct_name

                struct_fields = types.get(current_struct)
                if struct_fields is None:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f'Unknown struct type "{current_struct}" in EIP-712 schema.',
                    )

                index = next((i for i, (_, field_name) in enumerate(struct_fields) if field_name == name), None)
                if index is None:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f'Field "{name}" not found in struct "{current_struct}".',
                    )

                if index > _MAX_FIELD_INDEX:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f'Field "{name}" is the field {index} of struct "{current_struct}", the device '
                        f"addresses at most {_MAX_FIELD_INDEX + 1} fields.",
                    )

                elements.append(CalldataDescriptorEIP712PathElementStructFieldV1(index=index))
                current_parsed = parse_solidity_type(struct_fields[index][0])
                remaining_dims = len(current_parsed.array_dimensions)

            case Array():
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array selector applied to a non-array value.",
                    )
                selected *= _selected_count(_current_dimension(current_parsed, remaining_dims), None, None)
                elements.append(CalldataDescriptorEIP712PathElementArraySliceV1())
                remaining_dims -= 1

            case ArrayElement(index=array_index):
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array index applied to a non-array value.",
                    )
                dimension = _current_dimension(current_parsed, remaining_dims)
                if dimension is not None and not -dimension <= array_index < dimension:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Array index {array_index} is out of bounds for array of dimension {dimension}.",
                    )
                # a single element [i] is a slice [i, i+1); for i == -1, end defaults to the array length
                end = None if array_index == -1 else array_index + 1
                if (bound := _unrepresentable_bound(array_index, end)) is not None:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Array index {array_index} is not supported, the device cannot represent {bound}.",
                    )
                elements.append(CalldataDescriptorEIP712PathElementArraySliceV1(start=array_index, end=end))
                remaining_dims -= 1

            case ArraySlice(start=start, end=end) if (
                remaining_dims == 0
                and position == last_index
                and current_parsed is not None
                and current_parsed.sol_type in _SLICEABLE_LEAVES
            ):
                if _is_empty_leaf_slice(start, end):
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Leaf slice [{start}:{end}] is empty, the device refuses a slice with no byte.",
                    )
                if (bound := _unrepresentable_bound(start, end)) is not None:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Leaf slice [{start}:{end}] is not supported, the device cannot represent {bound}.",
                    )
                if current_parsed.sol_type == CalldataDescriptorEIP712SolType.BYTES_FIX and current_parsed.type_size:
                    # the length of the leaf is known: the slice has to be inside it and keep a byte
                    size = current_parsed.type_size
                    first = _resolve_bound(start, size, 0)
                    last = _resolve_bound(end, size, size)
                    if first < 0 or last > size:
                        return out.error(
                            title="Invalid EIP-712 path",
                            message=f"Leaf slice [{start}:{end}] is not inside the {size} bytes of the leaf.",
                        )
                    if last <= first:
                        return out.error(
                            title="Invalid EIP-712 path",
                            message=f"Leaf slice [{start}:{end}] is empty, the device refuses a slice with no byte.",
                        )
                    slice_width = last - first
                elements.append(CalldataDescriptorEIP712PathElementLeafSliceV1(start=start, end=end))
                leaf_sliced = True

            case ArraySlice(start=start, end=end):
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array slice applied to a non-array value.",
                    )
                if (bound := _unrepresentable_bound(start, end)) is not None:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Array slice [{start}:{end}] is not supported, the device cannot represent {bound}.",
                    )
                dimension = _current_dimension(current_parsed, remaining_dims)
                if dimension is not None and not _is_inside(start, end, dimension):
                    return out.error(
                        title="Invalid EIP-712 path",
                        message=f"Array slice [{start}:{end}] is out of bounds for array of dimension {dimension}.",
                    )
                selected *= _selected_count(dimension, start, end)
                elements.append(CalldataDescriptorEIP712PathElementArraySliceV1(start=start, end=end))
                remaining_dims -= 1

    if current_parsed is None:
        return out.error(
            title="Invalid EIP-712 path",
            message="EIP-712 path does not reference any field.",
        )

    if remaining_dims != 0:
        return out.error(
            title="Invalid EIP-712 path",
            message="EIP-712 path ends on an incompletely indexed array; a scalar leaf is required.",
        )

    if current_parsed.sol_type == CalldataDescriptorEIP712SolType.STRUCT:
        return out.error(
            title="Invalid EIP-712 path",
            message=f'EIP-712 path ends on struct "{current_parsed.struct_name}"; a scalar leaf is required.',
        )

    if len(elements) > MAX_EIP712_PATH_ELEMENTS:
        return out.error(
            title="Invalid EIP-712 path",
            message=f"EIP-712 path {data_path} has {len(elements)} elements, the device accepts at most "
            f"{MAX_EIP712_PATH_ELEMENTS}.",
        )

    if selected > _MAX_SELECTED_VALUES:
        return out.error(
            title="Invalid EIP-712 path",
            message=f"EIP-712 path {data_path} selects at least {selected} values, the device accepts at most "
            f"{_MAX_SELECTED_VALUES}.",
        )

    type_family, type_size = _leaf_type_family_size(current_parsed)
    if leaf_sliced:
        # the size of a slice is not the size of the type it is cut from, it is only known for a fixed size leaf
        type_size = slice_width

    return CalldataDescriptorValuePathV1(
        type_family=type_family,
        type_size=type_size,
        abi_path=data_path,
        binary_path=CalldataDescriptorEIP712PathV1(elements=elements),
    )
