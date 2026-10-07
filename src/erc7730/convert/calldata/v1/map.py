"""
Conversion of map lookups to device side maps: a MAP_REF value, looked up by the device in MAP_ENTRY structs.

The device reads the key from the transaction, then looks up the MAP_ENTRY provided by the wallet whose key matches it
byte for byte, so each map key is encoded exactly as the device reads the key value:
 - a static calldata value is a whole calldata chunk (ABI encoding on 32 bytes)
 - a dynamic calldata value (bytes, string) is its raw content
 - a sliced calldata value is the slice of the above
 - the chain id is a 64 bits big endian integer, the sender / target addresses are 20 bytes, the native value is a
   256 bits big endian integer

See doc/tlv_structs.md#map_entry in https://github.com/LedgerHQ/app-ethereum for specifications of these structs.
"""

from collections.abc import Callable
from typing import assert_never

from erc7730.common.abi import ABIDataType
from erc7730.common.binary import from_hex
from erc7730.common.output import OutputAdder
from erc7730.convert.calldata.v1.abi import ABITree
from erc7730.convert.calldata.v1.path import convert_container_path, convert_data_path
from erc7730.convert.calldata.v1.tlv import tlv_value
from erc7730.model.calldata.v1.instruction import MAX_MAP_ENTRY_SIZE, CalldataDescriptorInstructionMapEntryV1
from erc7730.model.calldata.v1.value import (
    CalldataDescriptorContainerPathV1,
    CalldataDescriptorContainerPathValueV1,
    CalldataDescriptorDataPathV1,
    CalldataDescriptorMapRefV1,
    CalldataDescriptorPathElementArrayV1,
    CalldataDescriptorPathElementLeafV1,
    CalldataDescriptorPathElementSliceV1,
    CalldataDescriptorPathLeafType,
    CalldataDescriptorTypeFamily,
    CalldataDescriptorValueMapRefV1,
    CalldataDescriptorValuePathV1,
)
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.resolved.v2.context import ResolvedDeployment
from erc7730.model.resolved.v2.display import ResolvedValueMap
from erc7730.model.types import Address, HexStr, Selector

# size of a calldata chunk (CALLDATA_CHUNK_SIZE in app-ethereum)
CALLDATA_CHUNK_SIZE = 32

# length of an EVM address (ADDRESS_LENGTH in app-ethereum)
ADDRESS_LENGTH = 20

# size of the chain id the device reads from the transaction context (uint64)
CHAIN_ID_SIZE = 8

# maximum size of the KEY VALUE struct embedded in a MAP_REF (MAP_REF_KEY_TLV_MAX_SIZE in app-ethereum)
MAP_REF_KEY_MAX_SIZE = 48

# map ids are encoded on a single byte
MAX_MAP_ID = 255

# reports why a map key is invalid, and returns None
_Invalid = Callable[[str], bytes | None]


class MapEntries:
    """
    Device side maps of a calldata descriptor (bound to a single deployment and selector).

    Map ids are allocated per descriptor: a map looked up several times with the same key and value encodings shares
    its id and MAP_ENTRY structs, a map looked up with different encodings (for instance its values read as addresses
    in one field and as strings in another) gets one id per encoding.
    """

    def __init__(self, deployment: ResolvedDeployment, selector: Selector) -> None:
        self.deployment = deployment
        self.selector = selector
        self.entries: list[CalldataDescriptorInstructionMapEntryV1] = []
        self._ids: dict[tuple[str, tuple[tuple[bytes, bytes], ...]], int] = {}

    def map_ref(
        self,
        value_map: ResolvedValueMap,
        abi_type: ABIDataType,
        abi: ABITree,
        out: OutputAdder,
    ) -> CalldataDescriptorValueMapRefV1 | None:
        """
        Convert a map lookup to a MAP_REF value, and register the MAP_ENTRY structs of the map.

        :param value_map: resolved map lookup
        :param abi_type: data type the map values are encoded with
        :param abi: function ABI tree
        :param out: error handler
        :return: MAP_REF value, or None on error
        """
        map_name = str(value_map.map)

        if (encoded_keys := encode_map_keys(value_map, abi, out)) is None:
            return None
        key, keys_bytes = encoded_keys

        encoded: list[tuple[str, bytes, bytes]] = []
        for key_source, value in value_map.values.items():
            key_bytes = keys_bytes[key_source]
            value_bytes = from_hex(value.raw)  # encoded with the parameter type when resolved
            if not 1 <= len(value_bytes) <= MAX_MAP_ENTRY_SIZE:
                return out.error(
                    title="Invalid map value",
                    message=f"""Value for key "{key_source}" of map {map_name} must encode to 1 to """
                    f"{MAX_MAP_ENTRY_SIZE} bytes, it encodes to {len(value_bytes)}.",
                )
            encoded.append((key_source, key_bytes, value_bytes))

        signature = (map_name, tuple(sorted((key_bytes, value_bytes) for _, key_bytes, value_bytes in encoded)))
        if (map_id := self._ids.get(signature)) is None:
            if (map_id := len(self._ids)) > MAX_MAP_ID:
                return out.error(
                    title="Too many maps",
                    message=f"At most {MAX_MAP_ID + 1} maps can be looked up in a single function.",
                )
            self._ids[signature] = map_id
            for key_source, key_bytes, value_bytes in encoded:
                self.entries.append(
                    CalldataDescriptorInstructionMapEntryV1(
                        chain_id=self.deployment.chainId,
                        address=Address(self.deployment.address),
                        selector=self.selector,
                        map=map_name,
                        id=map_id,
                        key_source=key_source,
                        key=HexStr("0x" + key_bytes.hex()),
                        value_source=value_map.values[key_source].value,
                        value=HexStr("0x" + value_bytes.hex()),
                    )
                )

        # the formatters only read the declared size to interpret signed integers and to check a minimum length,
        # which only holds if all the values have it
        value_sizes = {len(value_bytes) for _, _, value_bytes in encoded}
        return CalldataDescriptorValueMapRefV1(
            type_family=CalldataDescriptorTypeFamily[abi_type.name],
            type_size=value_sizes.pop() if len(value_sizes) == 1 else None,
            map_ref=CalldataDescriptorMapRefV1(map=map_name, id=map_id, key=key),
        )


def encode_map_keys(
    value_map: ResolvedValueMap, abi: ABITree, out: OutputAdder
) -> tuple[CalldataDescriptorValuePathV1, dict[str, bytes]] | None:
    """
    Convert the key path of a map lookup to the value the device reads the key from, and encode the map keys the way
    the device reads that value.

    :param value_map: resolved map lookup
    :param abi: function ABI tree
    :param out: error handler
    :return: value the device reads the key from, and encoded keys indexed by source key, or None on error
    """
    map_name = str(value_map.map)

    if (key := _convert_key_path(value_map, abi, out)) is None:
        return None

    if len(tlv_value(key)) > MAP_REF_KEY_MAX_SIZE:
        return out.error(
            title="Unsupported map key",
            message=f"Path {value_map.keyPath} used as key of map {map_name} is too complex: the device "
            f"accepts at most {MAP_REF_KEY_MAX_SIZE} bytes to encode it.",
        )

    keys_bytes: dict[str, bytes] = {}
    sources: dict[bytes, str] = {}
    valid = True
    for key_source in value_map.values:
        # all keys are checked, so that every invalid key is reported at once
        if (key_bytes := _encode_key(key_source, key, map_name, out)) is None:
            valid = False
            continue
        if (other_key := sources.get(key_bytes)) is not None:
            valid = False
            out.error(
                title="Invalid map key",
                message=f"""Keys "{other_key}" and "{key_source}" of map {map_name} encode to the same """
                f"{key.type_family.name.lower()} key.",
            )
            continue
        sources[key_bytes] = key_source
        keys_bytes[key_source] = key_bytes

    return (key, keys_bytes) if valid else None


def _convert_key_path(
    value_map: ResolvedValueMap, abi: ABITree, out: OutputAdder
) -> CalldataDescriptorValuePathV1 | None:
    """Convert the key path of a map lookup to the value the device reads the key from."""
    match value_map.keyPath:
        case ContainerPath() as container_path:
            return convert_container_path(container_path, out)

        case DataPath() as data_path:
            if (key := convert_data_path(data_path, abi, out)) is None:
                return None
            assert isinstance(key.binary_path, CalldataDescriptorDataPathV1)  # nosec B101 - data path converts to one

            # the device looks up a single key: it rejects a path reading several values
            for element in key.binary_path.elements:
                if isinstance(element, CalldataDescriptorPathElementArrayV1) and not _is_single_element(element):
                    return out.error(
                        title="Unsupported map key",
                        message=f"Path {data_path} used as key of map {value_map.map} references several values, a "
                        "map key must reference a single value.",
                    )
            return key

        case _:
            assert_never(value_map.keyPath)


def _is_single_element(element: CalldataDescriptorPathElementArrayV1) -> bool:
    """Whether an array path element selects a single array element."""
    match element.start, element.end:
        case int(start), int(end):
            return end == start + 1
        case -1, None:
            return True
        case _:
            return False


def _encode_key(key_source: str, key: CalldataDescriptorValuePathV1, map_name: str, out: OutputAdder) -> bytes | None:
    """
    Encode a map key the way the device reads the key value from the transaction.

    :param key_source: map key, as written in the source descriptor
    :param key: value the device reads the key from
    :param map_name: source map reference, for error messages
    :param out: error handler
    :return: encoded key, or None on error
    """

    def invalid(reason: str) -> bytes | None:
        out.error(
            title="Invalid map key",
            message=f"""Key "{key_source}" of map {map_name} cannot be matched against {key.abi_path}: {reason}.""",
        )
        return None

    match key.binary_path:
        case CalldataDescriptorContainerPathV1(value=container_value):
            match container_value:
                case CalldataDescriptorContainerPathValueV1.CHAIN_ID:
                    return _encode_uint(key_source, CHAIN_ID_SIZE, invalid)
                case CalldataDescriptorContainerPathValueV1.FROM | CalldataDescriptorContainerPathValueV1.TO:
                    return _encode_hex(key_source, ADDRESS_LENGTH, invalid, pad_left=True)
                case CalldataDescriptorContainerPathValueV1.VALUE:
                    return _encode_uint(key_source, CALLDATA_CHUNK_SIZE, invalid)
                case _:
                    assert_never(container_value)

        case CalldataDescriptorDataPathV1(elements=elements):
            leaf_slice: CalldataDescriptorPathElementSliceV1 | None = None
            if isinstance(elements[-1], CalldataDescriptorPathElementSliceV1):
                leaf_slice = elements[-1]
                elements = elements[:-1]
            if not isinstance(leaf := elements[-1], CalldataDescriptorPathElementLeafV1):
                return invalid("the key path does not end with a value")

            match leaf.leaf_type:
                case CalldataDescriptorPathLeafType.STATIC_LEAF:
                    length: int | None = CALLDATA_CHUNK_SIZE
                case CalldataDescriptorPathLeafType.DYNAMIC_LEAF:
                    length = None
                case _:
                    return invalid("the key path must reference a static or dynamic value")

            # a sliced key is written in the map as the slice itself, there is no way to tell the rest of the value
            if leaf_slice is not None:
                return _encode_sliced_key(key_source, key, length, leaf_slice, invalid)
            if length is not None:
                return _encode_static_key(key_source, key, invalid)
            return _encode_dynamic_key(key_source, key, invalid)

        case _:
            assert_never(key.binary_path)


def _encode_static_key(key_source: str, key: CalldataDescriptorValuePathV1, invalid: _Invalid) -> bytes | None:
    """Encode a key read from a static calldata value: the device reads the whole ABI encoded chunk."""
    match key.type_family:
        case CalldataDescriptorTypeFamily.UINT:
            if (encoded := _encode_uint(key_source, key.type_size or CALLDATA_CHUNK_SIZE, invalid)) is None:
                return None
            return encoded.rjust(CALLDATA_CHUNK_SIZE, b"\x00")
        case CalldataDescriptorTypeFamily.INT:
            if (value := _parse_int(key_source)) is None:
                return invalid("expected an integer")
            size = key.type_size or CALLDATA_CHUNK_SIZE
            bound = 1 << (size * 8 - 1)
            if not -bound <= value < bound:
                return invalid(f"it does not fit in {size} bytes")
            return value.to_bytes(CALLDATA_CHUNK_SIZE, byteorder="big", signed=True)
        case CalldataDescriptorTypeFamily.ADDRESS:
            if (encoded := _encode_hex(key_source, ADDRESS_LENGTH, invalid, pad_left=True)) is None:
                return None
            return encoded.rjust(CALLDATA_CHUNK_SIZE, b"\x00")
        case CalldataDescriptorTypeFamily.BOOL:
            if (encoded := _encode_bool(key_source, invalid)) is None:
                return None
            return encoded.rjust(CALLDATA_CHUNK_SIZE, b"\x00")
        case CalldataDescriptorTypeFamily.BYTES:
            # bytesN values are left aligned in their chunk
            if (encoded := _encode_hex(key_source, key.type_size or CALLDATA_CHUNK_SIZE, invalid)) is None:
                return None
            return encoded.ljust(CALLDATA_CHUNK_SIZE, b"\x00")
        case _:
            return invalid(f"{key.type_family.name.lower()} keys are not supported")


def _encode_dynamic_key(key_source: str, key: CalldataDescriptorValuePathV1, invalid: _Invalid) -> bytes | None:
    """Encode a key read from a dynamic calldata value: the device reads its raw content."""
    match key.type_family:
        case CalldataDescriptorTypeFamily.STRING:
            encoded = key_source.encode("utf-8")
        case CalldataDescriptorTypeFamily.BYTES:
            if (hex_encoded := _encode_hex(key_source, MAX_MAP_ENTRY_SIZE, invalid)) is None:
                return None
            encoded = hex_encoded
        case _:
            return invalid(f"dynamic {key.type_family.name.lower()} keys are not supported")
    return _check_key_size(encoded, invalid)


def _encode_sliced_key(
    key_source: str,
    key: CalldataDescriptorValuePathV1,
    length: int | None,
    leaf_slice: CalldataDescriptorPathElementSliceV1,
    invalid: _Invalid,
) -> bytes | None:
    """Encode a key read from a slice of a calldata value: the key is the slice itself."""
    width = _slice_width(length, leaf_slice)
    if width == 0:
        return invalid("the key path slice is empty")

    match key.type_family:
        case CalldataDescriptorTypeFamily.STRING:
            encoded = key_source.encode("utf-8")
        case CalldataDescriptorTypeFamily.UINT | CalldataDescriptorTypeFamily.INT if not key_source.startswith("0x"):
            if (value := _parse_int(key_source)) is None:
                return invalid("expected an integer")
            signed = key.type_family is CalldataDescriptorTypeFamily.INT
            try:
                encoded = value.to_bytes(
                    width or max(1, (value.bit_length() + 8 * signed + 7) // 8), byteorder="big", signed=signed
                )
            except OverflowError:
                return invalid(f"it does not fit in the {width} bytes of the slice")
        case CalldataDescriptorTypeFamily.BOOL if not key_source.startswith("0x"):
            if (encoded_bool := _encode_bool(key_source, invalid)) is None:
                return None
            encoded = encoded_bool.rjust(width or 1, b"\x00")
        case _:
            # numbers and addresses are right aligned in the value they are sliced from
            pad_left = key.type_family in (CalldataDescriptorTypeFamily.UINT, CalldataDescriptorTypeFamily.ADDRESS)
            if (hex_encoded := _encode_hex(key_source, width or MAX_MAP_ENTRY_SIZE, invalid, pad_left)) is None:
                return None
            encoded = hex_encoded

    if width is not None and len(encoded) != width:
        return invalid(f"it encodes to {len(encoded)} bytes, but the key path slice is {width} bytes")
    return _check_key_size(encoded, invalid)


def _slice_width(length: int | None, leaf_slice: CalldataDescriptorPathElementSliceV1) -> int | None:
    """Width of a slice, when it can be known at conversion time (the device applies it as python slices do)."""
    start, end = leaf_slice.start, leaf_slice.end
    if length is not None:
        return len(range(length)[start:end])
    match start, end:
        case None, int(end) if end >= 0:
            return end
        case int(start), None if start < 0:
            return -start
        case int(start), int(end) if (start >= 0) == (end >= 0):
            return max(0, end - start)
        case _:
            return None


def _check_key_size(encoded: bytes, invalid: _Invalid) -> bytes | None:
    if not 1 <= len(encoded) <= MAX_MAP_ENTRY_SIZE:
        return invalid(f"a key must encode to 1 to {MAX_MAP_ENTRY_SIZE} bytes, it encodes to {len(encoded)}")
    return encoded


def _parse_int(key_source: str) -> int | None:
    try:
        return int(key_source, 16) if key_source.lower().startswith("0x") else int(key_source, 10)
    except ValueError:
        return None


def _encode_uint(key_source: str, size: int, invalid: _Invalid) -> bytes | None:
    if (value := _parse_int(key_source)) is None or value < 0:
        return invalid("expected an unsigned integer")
    if value.bit_length() > size * 8:
        return invalid(f"it does not fit in {size} bytes")
    return value.to_bytes(size, byteorder="big")


def _encode_hex(key_source: str, size: int, invalid: _Invalid, pad_left: bool = False) -> bytes | None:
    """Decode a hex key of at most size bytes, left padded to size bytes if requested."""
    if not key_source.startswith("0x"):
        return invalid("expected a hexadecimal string")
    try:
        encoded = from_hex(key_source)
    except ValueError:
        return invalid("expected a hexadecimal string")
    if not 1 <= len(encoded) <= size:
        return invalid(f"expected 1 to {size} bytes, got {len(encoded)}")
    return encoded.rjust(size, b"\x00") if pad_left else encoded


def _encode_bool(key_source: str, invalid: _Invalid) -> bytes | None:
    match key_source.lower():
        case "true" | "1":
            return b"\x01"
        case "false" | "0":
            return b"\x00"
        case _:
            return invalid("expected a boolean")
