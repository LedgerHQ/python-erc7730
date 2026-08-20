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
    CalldataDescriptorEIP712PathElementArraySliceV1,
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

    for element in data_path.elements:
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

                elements.append(CalldataDescriptorEIP712PathElementStructFieldV1(index=index))
                current_parsed = parse_solidity_type(struct_fields[index][0])
                remaining_dims = len(current_parsed.array_dimensions)

            case Array():
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array selector applied to a non-array value.",
                    )
                elements.append(CalldataDescriptorEIP712PathElementArraySliceV1())
                remaining_dims -= 1

            case ArrayElement(index=array_index):
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array index applied to a non-array value.",
                    )
                # a single element [i] is a slice [i, i+1); for i == -1, end defaults to the array length
                end = None if array_index == -1 else array_index + 1
                elements.append(CalldataDescriptorEIP712PathElementArraySliceV1(start=array_index, end=end))
                remaining_dims -= 1

            case ArraySlice(start=start, end=end):
                if remaining_dims <= 0:
                    return out.error(
                        title="Invalid EIP-712 path",
                        message="Array slice applied to a non-array value.",
                    )
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

    type_family, type_size = _leaf_type_family_size(current_parsed)

    return CalldataDescriptorValuePathV1(
        type_family=type_family,
        type_size=type_size,
        abi_path=data_path,
        binary_path=CalldataDescriptorEIP712PathV1(elements=elements),
    )
