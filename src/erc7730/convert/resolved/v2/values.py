from collections.abc import Mapping
from typing import Any, assert_never

from pydantic import TypeAdapter, ValidationError

from erc7730.common.abi import ABIDataType
from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.v2.constants import ConstantProvider
from erc7730.model.input.v2.display import InputFieldBase, InputMapReference
from erc7730.model.input.v2.format import FieldFormat
from erc7730.model.paths import ContainerField, ContainerPath, DataPath, DescriptorPath
from erc7730.model.paths.path_ops import data_or_container_path_concat
from erc7730.model.resolved.display import ResolvedValue, ResolvedValueConstant, ResolvedValuePath
from erc7730.model.resolved.v2.display import ResolvedValueMap, ResolvedValueOrMap
from erc7730.model.types import HexStr, ScalarType


def resolve_field_value(
    prefix: DataPath,
    input_field: InputFieldBase,
    input_field_format: FieldFormat | None,
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedValue | None:
    """
    Resolve value, as a data path or constant value, for a field or reference.

    :param prefix: current path prefix
    :param input_field: field description or definition
    :param input_field_format: input field format
    :param constants: descriptor paths constants resolver
    :param out: error handler
    :return: resolved value or None if error
    """
    match input_field_format:
        case None | FieldFormat.RAW:
            abi_type = ABIDataType.STRING
        case (
            FieldFormat.AMOUNT
            | FieldFormat.TOKEN_AMOUNT
            | FieldFormat.DURATION
            | FieldFormat.DATE
            | FieldFormat.UNIT
            | FieldFormat.NFT_NAME
            | FieldFormat.ENUM
        ):
            abi_type = ABIDataType.UINT
        case FieldFormat.ADDRESS_NAME | FieldFormat.INTEROPERABLE_ADDRESS_NAME:
            abi_type = ABIDataType.ADDRESS
        case FieldFormat.CALL_DATA:
            abi_type = ABIDataType.BYTES
        case FieldFormat.TOKEN_TICKER:
            abi_type = ABIDataType.ADDRESS
        case FieldFormat.CHAIN_ID:
            abi_type = ABIDataType.UINT
        case _:
            assert_never(input_field_format)

    if (
        value := resolve_path_or_constant_value(
            prefix=prefix,
            input_path=input_field.path,
            input_value=input_field.value,
            abi_type=abi_type,
            constants=constants,
            out=out,
        )
    ) is None:
        return out.error(title="Invalid field", message="Field must have either a path or a value.")
    return value


def resolve_path_or_constant_value(
    prefix: DataPath,
    input_path: DescriptorPath | DataPath | ContainerPath | None,
    input_value: DescriptorPath | ScalarType | None,
    abi_type: ABIDataType,
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedValue | None:
    """
    Resolve value, as a data path or constant value.

    :param prefix: current path prefix
    :param input_path: input data path, if provided
    :param input_value: input constant value, if provided
    :param abi_type: expected encoded value data type
    :param constants: descriptor paths constants resolver
    :param out: error handler
    :return: resolved value or None if error or value resolves to None
    """
    if input_path is not None:
        if input_value is not None:
            return out.error(
                title="Invalid field",
                message="Field cannot have both a path and a value.",
            )

        if (path := constants.resolve_path(input_path, out)) is None:
            return None

        return ResolvedValuePath(path=data_or_container_path_concat(prefix, path))

    if input_value is not None:
        if (value := constants.resolve(input_value, out)) is None:
            return None

        if not isinstance(value, str | bool | int | float):
            return out.error(
                title="Invalid constant value",
                message="Constant value must be a scalar type (string, boolean or number).",
            )

        if (raw := encode_value(value, abi_type, out)) is None:
            return None

        return ResolvedValueConstant(type_family=abi_type, type_size=len(raw) // 2 - 1, value=value, raw=raw)

    return None


def resolve_path_constant_or_map_value(
    prefix: DataPath,
    input_path: DescriptorPath | DataPath | ContainerPath | None,
    input_value: DescriptorPath | ScalarType | InputMapReference | None,
    abi_type: ABIDataType,
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedValueOrMap | None:
    """
    Resolve value, as a data path, constant value or map lookup.

    :param prefix: current path prefix
    :param input_path: input data path, if provided
    :param input_value: input constant value or map reference, if provided
    :param abi_type: expected encoded value data type
    :param constants: descriptor paths constants resolver
    :param out: error handler
    :return: resolved value or None if error or value resolves to None
    """
    if not isinstance(input_value, InputMapReference):
        return resolve_path_or_constant_value(prefix, input_path, input_value, abi_type, constants, out)

    if input_path is not None:
        return out.error(
            title="Invalid field",
            message="Field cannot have both a path and a value.",
        )

    return resolve_map_reference_value(prefix, input_value, abi_type, constants, out)


def resolve_map_reference_value(
    prefix: DataPath,
    map_ref: InputMapReference,
    abi_type: ABIDataType,
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedValueConstant | ResolvedValueMap | None:
    """
    Resolve a map reference, as a constant value if the key is a constant, or as a map lookup otherwise.

    :param prefix: current path prefix
    :param map_ref: input map reference
    :param abi_type: expected encoded value data type
    :param constants: descriptor paths constants resolver
    :param out: error handler
    :return: resolved value or None if error
    """
    map_def = constants.get(map_ref.map, out)
    if map_def is None:
        return None
    if not isinstance(values := getattr(map_def, "values", None), dict):
        return out.error(
            title="Invalid map reference",
            message=f"{map_ref.map} is not a valid map definition.",
        )

    def resolve_map_value(key: str, value: Any) -> ResolvedValueConstant | None:
        if not isinstance(value, str | bool | int | float):
            return out.error(
                title="Invalid map value",
                message=f"""Value for key "{key}" in map {map_ref.map} must be a scalar type (string, boolean or """
                "number).",
            )
        if (raw := encode_value(value, abi_type, out)) is None:
            return None
        return ResolvedValueConstant(type_family=abi_type, type_size=len(raw) // 2 - 1, value=value, raw=raw)

    # a key that is itself a constant selects the value right away, other map values are not used
    if isinstance(map_ref.keyPath, DescriptorPath):
        if (key := constants.get(map_ref.keyPath, out)) is None:
            return None
        if (map_key := lookup_map_key(values, str(key))) is None:
            return out.error(
                title="Invalid map reference",
                message=f"""Map {map_ref.map} has no value for key "{key}" (from {map_ref.keyPath}).""",
            )
        return resolve_map_value(map_key, values[map_key])

    resolved_values: dict[str, ResolvedValueConstant] = {}
    for key, value in values.items():
        if (resolved_value := resolve_map_value(key, value)) is None:
            return None
        resolved_values[key] = resolved_value

    if (key_path := constants.resolve_path(map_ref.keyPath, out)) is None:
        return None

    return ResolvedValueMap(keyPath=data_or_container_path_concat(prefix, key_path), values=resolved_values)


def deployment_map_key(key_path: ContainerPath | DataPath, chain_id: int, address: str) -> str | None:
    """
    Get the map key a deployment provides, for map lookups keyed on the chain id or target contract address.

    :param key_path: resolved map key path
    :param chain_id: deployment chain id
    :param address: deployment contract address
    :return: map key, or None if the key is not determined by the deployment
    """
    if isinstance(key_path, ContainerPath):
        match key_path.field:
            case ContainerField.CHAIN_ID:
                return str(chain_id)
            case ContainerField.TO:
                return address
            case ContainerField.FROM | ContainerField.VALUE:
                return None
            case _:
                assert_never(key_path.field)
    return None


def lookup_map_value(values: dict[str, ResolvedValueConstant], key: str) -> ResolvedValueConstant | None:
    """
    Look up a map value, matching hex keys (addresses) case-insensitively.

    :param values: resolved map values, indexed by key
    :param key: map key
    :return: resolved constant value, or None if the map has no value for the key
    """
    if (map_key := lookup_map_key(values, key)) is None:
        return None
    return values[map_key]


def lookup_map_key(values: Mapping[str, Any], key: str) -> str | None:
    """
    Find the map key matching a key, matching hex keys (addresses) case-insensitively.

    :param values: map values, indexed by key
    :param key: map key
    :return: matching map key, or None if the map has no value for the key
    """
    if key in values:
        return key
    if key.startswith("0x"):
        for map_key in values:
            if map_key.lower() == key.lower():
                return map_key
    return None


def encode_value(value: ScalarType, abi_type: ABIDataType, out: OutputAdder) -> HexStr | None:
    if isinstance(value, str) and value.startswith("0x"):
        try:
            hex_value = TypeAdapter(HexStr).validate_strings(value)
        except ValidationError:
            return out.error(
                title="Invalid hex string",
                message=f""""{value}" is not a valid hexadecimal string.""",
            )
        if abi_type == ABIDataType.ADDRESS and len(hex_value) != 42:
            return out.error(title="Invalid constant", message=f"""Value "{value}" is not a valid 20 bytes address.""")
        return hex_value

    # this uses a custom specific encoding because this is what the Ledger app expects
    try:
        match abi_type:
            case ABIDataType.UFIXED | ABIDataType.FIXED:
                return out.error(title="Invalid constant", message="""Fixed precision numbers are not supported""")

            case ABIDataType.UINT:
                if not isinstance(value, int) or value < 0:
                    return out.error(title="Invalid constant", message=f"""Value "{value}" is not an unsigned int""")
                encoded = value.to_bytes(
                    length=(max(value.bit_length(), 1) + 7) // 8,
                    byteorder="big",
                    signed=False,
                )

            case ABIDataType.INT:
                if not isinstance(value, int):
                    return out.error(title="Invalid constant", message=f"""Value "{value}" is not an integer""")
                encoded = value.to_bytes(
                    length=(max(value.bit_length(), 1) + 7) // 8,
                    byteorder="big",
                    signed=True,
                )

            case ABIDataType.BOOL:
                if not isinstance(value, bool):
                    return out.error(title="Invalid constant", message=f"""Value "{value}" is not a boolean""")
                encoded = int(value).to_bytes(length=1, byteorder="big", signed=False)

            case ABIDataType.STRING:
                if not isinstance(value, str):
                    return out.error(title="Invalid constant", message=f"""Value "{value}" is not a string""")
                encoded = value.encode(encoding="ascii", errors="replace")

            case ABIDataType.ADDRESS:
                return out.error(
                    title="Invalid constant", message=f"""Value "{value}" is not a valid address hexadecimal string."""
                )

            case ABIDataType.BYTES:
                return out.error(
                    title="Invalid constant", message=f"""Value "{value}" is not a valid hexadecimal string."""
                )

            case _:
                assert_never(abi_type)
    except OverflowError:
        return out.error(
            title="Invalid constant",
            message=f"""Value "{value}" is too large for the specified type.""",
        )

    return HexStr("0x" + encoded.hex())
