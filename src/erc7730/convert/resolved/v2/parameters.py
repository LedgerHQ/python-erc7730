from typing import Any, assert_never, cast

from erc7730.common.abi import ABIDataType
from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.v2.constants import ConstantProvider
from erc7730.convert.resolved.v2.enums import get_enum, get_enum_id
from erc7730.convert.resolved.v2.values import resolve_path_or_constant_value
from erc7730.model.input.path import DescriptorPathStr
from erc7730.model.input.v2.common import InputMapReference
from erc7730.model.input.v2.display import (
    InputAddressNameParameters,
    InputCallDataParameters,
    InputDateParameters,
    InputEncryptionParameters,
    InputEnumParameters,
    InputFieldParameters,
    InputInteroperableAddressNameParameters,
    InputNftNameParameters,
    InputTokenAmountParameters,
    InputTokenTickerParameters,
    InputUnitParameters,
)
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.paths.path_ops import data_or_container_path_concat
from erc7730.model.resolved.display import ResolvedValue
from erc7730.model.resolved.metadata import EnumDefinition
from erc7730.model.resolved.v2.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedDateParameters,
    ResolvedEncryptionParameters,
    ResolvedEnumParameters,
    ResolvedFieldParameters,
    ResolvedInteroperableAddressNameParameters,
    ResolvedNftNameParameters,
    ResolvedTokenAmountParameters,
    ResolvedTokenTickerParameters,
    ResolvedUnitParameters,
)
from erc7730.model.types import Address, HexStr, Id, MixedCaseAddress


def _handle_map_reference(
    map_ref: InputMapReference,
    param_name: str,
    prefix: DataPath,
    constants: ConstantProvider,
    strict_maps: bool,
    out: OutputAdder,
) -> None:
    """Validate and handle a map reference.

    Always validates that the map exists in metadata.maps and the keyPath is valid.
    In strict mode (calldata/convert), emits an error. In lenient mode (lint), the
    value will be dropped after validation.
    """
    constants.resolve_map_reference(prefix, map_ref, out)

    if strict_maps:
        out.error(
            title="Unsupported map reference",
            message=f"Map references are not yet supported for {param_name}. Map at {map_ref.map} with "
            f"keyPath {map_ref.keyPath} cannot be resolved.",
        )


def resolve_field_parameters(
    prefix: DataPath,
    params: InputFieldParameters | None,
    enums: dict[Id, EnumDefinition],
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedFieldParameters | None:
    match params:
        case None:
            return None
        case InputAddressNameParameters():
            return resolve_address_name_parameters(prefix, params, constants, out, strict_maps=strict_maps)
        case InputInteroperableAddressNameParameters():
            return resolve_interoperable_address_name_parameters(
                prefix, params, constants, out, strict_maps=strict_maps
            )
        case InputCallDataParameters():
            return resolve_calldata_parameters(prefix, params, constants, out, strict_maps=strict_maps)
        case InputTokenAmountParameters():
            return resolve_token_amount_parameters(prefix, params, constants, out, strict_maps=strict_maps)
        case InputTokenTickerParameters():
            return resolve_token_ticker_parameters(prefix, params, constants, out, strict_maps=strict_maps)
        case InputNftNameParameters():
            return resolve_nft_parameters(prefix, params, constants, out, strict_maps=strict_maps)
        case InputDateParameters():
            return resolve_date_parameters(prefix, params, constants, out)
        case InputUnitParameters():
            return resolve_unit_parameters(prefix, params, constants, out)
        case InputEnumParameters():
            return resolve_enum_parameters(prefix, params, enums, constants, out)
        case _:
            assert_never(params)


def resolve_address_name_parameters(
    prefix: DataPath,
    params: InputAddressNameParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedAddressNameParameters | None:
    sender_address: list[Address] | None = None
    if (sender_addr_input := params.senderAddress) is not None:
        if isinstance(sender_addr_input, InputMapReference):
            _handle_map_reference(sender_addr_input, "senderAddress", prefix, constants, strict_maps, out)
            if strict_maps:
                return None
            sender_address = None
        else:
            resolved_sender = constants.resolve_or_none(sender_addr_input, out)
            if resolved_sender is None:
                sender_address = None
            elif isinstance(resolved_sender, str):
                sender_address = [Address(resolved_sender)]
            elif isinstance(resolved_sender, list):
                sender_address = [Address(addr) for addr in resolved_sender]
            else:
                raise Exception("Invalid senderAddress type")

    return ResolvedAddressNameParameters(
        types=constants.resolve_or_none(params.types, out),
        sources=constants.resolve_or_none(params.sources, out),
        senderAddress=sender_address,
    )


def resolve_interoperable_address_name_parameters(
    prefix: DataPath,
    params: InputInteroperableAddressNameParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedInteroperableAddressNameParameters | None:
    sender_address: list[Address] | None = None
    if (sender_addr_input := params.senderAddress) is not None:
        if isinstance(sender_addr_input, InputMapReference):
            _handle_map_reference(sender_addr_input, "senderAddress", prefix, constants, strict_maps, out)
            if strict_maps:
                return None
            sender_address = None
        else:
            resolved_sender = constants.resolve_or_none(sender_addr_input, out)
            if resolved_sender is None:
                sender_address = None
            elif isinstance(resolved_sender, str):
                sender_address = [Address(resolved_sender)]
            elif isinstance(resolved_sender, list):
                sender_address = [Address(addr) for addr in resolved_sender]
            else:
                raise Exception("Invalid senderAddress type")

    return ResolvedInteroperableAddressNameParameters(
        types=constants.resolve_or_none(params.types, out),
        sources=constants.resolve_or_none(params.sources, out),
        senderAddress=sender_address,
    )


def resolve_calldata_parameters(
    prefix: DataPath,
    params: InputCallDataParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedCallDataParameters | None:
    callee_resolved = None
    if params.callee is not None and isinstance(params.callee, InputMapReference):
        _handle_map_reference(params.callee, "callee", prefix, constants, strict_maps, out)
        return None
    elif params.callee is not None or params.calleePath is not None:
        callee_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.calleePath,
            input_value=params.callee,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
        if callee_resolved is None:
            return None

    selector_resolved = None
    if params.selector is not None and isinstance(params.selector, InputMapReference):
        _handle_map_reference(params.selector, "selector", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    elif params.selector is not None or params.selectorPath is not None:
        selector_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.selectorPath,
            input_value=params.selector,
            abi_type=ABIDataType.STRING,
            constants=constants,
            out=out,
        )

    amount_resolved = None
    if params.amount is not None and isinstance(params.amount, InputMapReference):
        _handle_map_reference(params.amount, "amount", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    elif params.amount is not None or params.amountPath is not None:
        amount_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.amountPath,
            input_value=params.amount,
            abi_type=ABIDataType.UINT,
            constants=constants,
            out=out,
        )

    spender_resolved = None
    if params.spender is not None and isinstance(params.spender, InputMapReference):
        _handle_map_reference(params.spender, "spender", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    elif params.spender is not None or params.spenderPath is not None:
        spender_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.spenderPath,
            input_value=params.spender,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )

    return ResolvedCallDataParameters(
        callee=cast(ResolvedValue, callee_resolved),
        selector=selector_resolved,
        amount=amount_resolved,
        spender=spender_resolved,
    )


def resolve_token_amount_parameters(
    prefix: DataPath,
    params: InputTokenAmountParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedTokenAmountParameters | None:
    token_value = params.token
    token_resolved = None
    if token_value is not None and isinstance(token_value, InputMapReference):
        _handle_map_reference(token_value, "token", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    else:
        token_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.tokenPath,
            input_value=token_value,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )

    resolved_addresses: list[Address] | None
    if isinstance(params.nativeCurrencyAddress, InputMapReference):
        _handle_map_reference(
            params.nativeCurrencyAddress, "nativeCurrencyAddress", prefix, constants, strict_maps, out
        )
        if strict_maps:
            return None
        resolved_addresses = None
    else:
        input_addresses = cast(
            list[DescriptorPathStr | MixedCaseAddress] | MixedCaseAddress | None,
            constants.resolve_or_none(params.nativeCurrencyAddress, out),
        )
        if input_addresses is None:
            resolved_addresses = None
        elif isinstance(input_addresses, list):
            resolved_addresses = []
            for input_address in input_addresses:
                if (resolved_address := constants.resolve(input_address, out)) is None:
                    return None
                resolved_addresses.append(Address(resolved_address))
        elif isinstance(input_addresses, str):
            resolved_addresses = [Address(input_addresses)]
        else:
            raise Exception("Invalid nativeCurrencyAddress type")

    if isinstance(params.threshold, InputMapReference):
        _handle_map_reference(params.threshold, "threshold", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
        resolved_threshold: HexStr | None = None
    else:
        input_threshold = cast(HexStr | int | None, constants.resolve_or_none(params.threshold, out))
        if input_threshold is not None:
            if isinstance(input_threshold, int):
                resolved_threshold = "0x" + input_threshold.to_bytes(byteorder="big", signed=False).hex()
            else:
                resolved_threshold = input_threshold
        else:
            resolved_threshold = None

    if isinstance(params.message, InputMapReference):
        _handle_map_reference(params.message, "message", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
        resolved_message: str | None = None
    else:
        resolved_message = constants.resolve_or_none(params.message, out)

    chain_id_value = params.chainId
    resolved_chain_id: int | None = None
    if chain_id_value is not None and isinstance(chain_id_value, InputMapReference):
        _handle_map_reference(chain_id_value, "chainId", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    elif chain_id_value is not None:
        if isinstance(chain_id_value, int):
            resolved_chain_id = chain_id_value
        else:
            resolved_value: Any = constants.resolve(chain_id_value, out)
            if isinstance(resolved_value, int):
                resolved_chain_id = resolved_value

    return ResolvedTokenAmountParameters(
        token=token_resolved,
        nativeCurrencyAddress=resolved_addresses,
        threshold=resolved_threshold,
        message=resolved_message,
        chainId=resolved_chain_id,
        chainIdPath=params.chainIdPath,
    )


def resolve_token_ticker_parameters(
    prefix: DataPath,
    params: InputTokenTickerParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedTokenTickerParameters | None:
    chain_id_value = params.chainId
    resolved_chain_id: int | None = None
    if chain_id_value is not None and isinstance(chain_id_value, InputMapReference):
        _handle_map_reference(chain_id_value, "chainId", prefix, constants, strict_maps, out)
        if strict_maps:
            return None
    elif chain_id_value is not None:
        if isinstance(chain_id_value, int):
            resolved_chain_id = chain_id_value
        else:
            resolved_value: Any = constants.resolve(chain_id_value, out)
            if isinstance(resolved_value, int):
                resolved_chain_id = resolved_value

    # Resolve and normalize chainIdPath using constants and the current prefix
    resolved_chain_id_path: DataPath | ContainerPath | None = None
    if params.chainIdPath is not None:
        relative_chain_id_path = constants.resolve_path(params.chainIdPath, out)
        if relative_chain_id_path is not None:
            resolved_chain_id_path = data_or_container_path_concat(prefix, relative_chain_id_path)

    return ResolvedTokenTickerParameters(
        chainId=resolved_chain_id,
        chainIdPath=resolved_chain_id_path,
    )


def resolve_nft_parameters(
    prefix: DataPath,
    params: InputNftNameParameters,
    constants: ConstantProvider,
    out: OutputAdder,
    *,
    strict_maps: bool = False,
) -> ResolvedNftNameParameters | None:
    collection_value = params.collection
    if collection_value is not None and isinstance(collection_value, InputMapReference):
        _handle_map_reference(collection_value, "collection", prefix, constants, strict_maps, out)
        return None
    else:
        collection_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.collectionPath,
            input_value=collection_value,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
        if collection_resolved is None:
            return None
        return ResolvedNftNameParameters(collection=collection_resolved)


def resolve_date_parameters(
    prefix: DataPath, params: InputDateParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedDateParameters | None:
    return ResolvedDateParameters(encoding=constants.resolve(params.encoding, out))


def resolve_unit_parameters(
    prefix: DataPath, params: InputUnitParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedUnitParameters | None:
    return ResolvedUnitParameters(
        base=constants.resolve(params.base, out),
        decimals=constants.resolve_or_none(params.decimals, out),
        prefix=constants.resolve_or_none(params.prefix, out),
    )


def resolve_enum_parameters(
    prefix: DataPath,
    params: InputEnumParameters,
    enums: dict[Id, EnumDefinition],
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedEnumParameters | None:
    if get_enum_id(params.ref, out) is None:
        return None
    if get_enum(params.ref, enums, out) is None:
        return None

    return ResolvedEnumParameters.model_validate({"$ref": str(params.ref)})


def resolve_encryption_parameters(
    prefix: DataPath, params: InputEncryptionParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedEncryptionParameters | None:
    # Encryption parameters are passed through as-is
    return ResolvedEncryptionParameters(
        scheme=params.scheme,
        plaintextType=params.plaintextType,
        fallbackLabel=params.fallbackLabel,
    )
