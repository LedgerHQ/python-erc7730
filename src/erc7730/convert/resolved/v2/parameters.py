from typing import Any, assert_never, cast

from erc7730.common.abi import ABIDataType
from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.v2.constants import ConstantProvider
from erc7730.convert.resolved.v2.enums import get_enum, get_enum_id
from erc7730.convert.resolved.v2.values import (
    resolve_map_reference_value,
    resolve_path_constant_or_map_value,
)
from erc7730.model.input.path import DescriptorPathStr
from erc7730.model.input.v2.display import (
    InputAddressNameParameters,
    InputCallDataParameters,
    InputDateParameters,
    InputEncryptionParameters,
    InputEnumParameters,
    InputFieldParameters,
    InputInteroperableAddressNameParameters,
    InputMapReference,
    InputNftNameParameters,
    InputTokenAmountParameters,
    InputTokenTickerParameters,
    InputUnitParameters,
)
from erc7730.model.paths import ContainerPath, DataPath, DescriptorPath
from erc7730.model.paths.path_ops import data_or_container_path_concat
from erc7730.model.resolved.display import ResolvedValueConstant
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
    ResolvedValueMap,
    ResolvedValueOrMap,
)
from erc7730.model.types import Address, HexStr, Id, MixedCaseAddress, ScalarType


def resolve_field_parameters(
    prefix: DataPath,
    params: InputFieldParameters | None,
    enums: dict[Id, EnumDefinition],
    constants: ConstantProvider,
    out: OutputAdder,
) -> ResolvedFieldParameters | None:
    match params:
        case None:
            return None
        case InputAddressNameParameters():
            return resolve_address_name_parameters(prefix, params, constants, out)
        case InputInteroperableAddressNameParameters():
            return resolve_interoperable_address_name_parameters(prefix, params, constants, out)
        case InputCallDataParameters():
            return resolve_calldata_parameters(prefix, params, constants, out)
        case InputTokenAmountParameters():
            return resolve_token_amount_parameters(prefix, params, constants, out)
        case InputTokenTickerParameters():
            return resolve_token_ticker_parameters(prefix, params, constants, out)
        case InputNftNameParameters():
            return resolve_nft_parameters(prefix, params, constants, out)
        case InputDateParameters():
            return resolve_date_parameters(prefix, params, constants, out)
        case InputUnitParameters():
            return resolve_unit_parameters(prefix, params, constants, out)
        case InputEnumParameters():
            return resolve_enum_parameters(prefix, params, enums, constants, out)
        case _:
            assert_never(params)


def resolve_address_name_parameters(
    prefix: DataPath, params: InputAddressNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedAddressNameParameters | None:
    sender_address = _resolve_sender_address(prefix, params.senderAddress, constants, out)
    if params.senderAddress is not None and sender_address is None:
        return None

    return ResolvedAddressNameParameters(
        types=constants.resolve_or_none(params.types, out),
        sources=constants.resolve_or_none(params.sources, out),
        senderAddress=sender_address,
    )


def resolve_interoperable_address_name_parameters(
    prefix: DataPath, params: InputInteroperableAddressNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedInteroperableAddressNameParameters | None:
    sender_address = _resolve_sender_address(prefix, params.senderAddress, constants, out)
    if params.senderAddress is not None and sender_address is None:
        return None

    return ResolvedInteroperableAddressNameParameters(
        types=constants.resolve_or_none(params.types, out),
        sources=constants.resolve_or_none(params.sources, out),
        senderAddress=sender_address,
    )


def _resolve_sender_address(
    prefix: DataPath,
    sender_addr_input: MixedCaseAddress | list[MixedCaseAddress] | DescriptorPath | InputMapReference | None,
    constants: ConstantProvider,
    out: OutputAdder,
) -> list[Address] | ResolvedValueMap | None:
    if sender_addr_input is None:
        return None

    if isinstance(sender_addr_input, InputMapReference):
        match resolved_map := resolve_map_reference_value(
            prefix, sender_addr_input, ABIDataType.ADDRESS, constants, out
        ):
            case ResolvedValueConstant():
                return [Address(str(resolved_map.value))]
            case _:
                return resolved_map

    resolved_sender = constants.resolve_or_none(sender_addr_input, out)
    if resolved_sender is None:
        return None
    if isinstance(resolved_sender, str):
        return [Address(resolved_sender)]
    if isinstance(resolved_sender, list):
        return [Address(addr) for addr in resolved_sender]
    raise Exception("Invalid senderAddress type")


def resolve_calldata_parameters(
    prefix: DataPath, params: InputCallDataParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedCallDataParameters | None:
    resolution_failed = False

    def resolve(
        input_path: DescriptorPath | DataPath | ContainerPath | None,
        input_value: DescriptorPath | ScalarType | InputMapReference | None,
        abi_type: ABIDataType,
    ) -> ResolvedValueOrMap | None:
        nonlocal resolution_failed
        resolved = resolve_path_constant_or_map_value(prefix, input_path, input_value, abi_type, constants, out)
        if resolved is None and (input_path is not None or input_value is not None):
            resolution_failed = True
        return resolved

    # callee is mandatory, other parameters are optional: each can be a path, a constant or a map reference
    if params.callee is None and params.calleePath is None:
        return out.error(
            title="Missing callee",
            message='Calldata parameters must set either "callee" or "calleePath".',
        )
    if (callee_resolved := resolve(params.calleePath, params.callee, ABIDataType.ADDRESS)) is None:
        return None

    selector_resolved = resolve(params.selectorPath, params.selector, ABIDataType.STRING)
    amount_resolved = resolve(params.amountPath, params.amount, ABIDataType.UINT)
    spender_resolved = resolve(params.spenderPath, params.spender, ABIDataType.ADDRESS)
    if resolution_failed:
        return None

    return ResolvedCallDataParameters(
        callee=callee_resolved,
        selector=selector_resolved,
        amount=amount_resolved,
        spender=spender_resolved,
    )


def resolve_token_amount_parameters(
    prefix: DataPath, params: InputTokenAmountParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedTokenAmountParameters | None:
    # Resolve token into a ResolvedValue (path or constant) like v1, or into a map lookup.
    token_resolved = resolve_path_constant_or_map_value(
        prefix=prefix,
        input_path=params.tokenPath,
        input_value=params.token,
        abi_type=ABIDataType.ADDRESS,
        constants=constants,
        out=out,
    )
    if token_resolved is None and (params.token is not None or params.tokenPath is not None):
        return None

    input_addresses = cast(
        list[DescriptorPathStr | MixedCaseAddress] | MixedCaseAddress | None,
        constants.resolve_or_none(params.nativeCurrencyAddress, out),
    )
    resolved_addresses: list[Address] | None
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

    input_threshold = cast(HexStr | int | None, constants.resolve_or_none(params.threshold, out))
    resolved_threshold: HexStr | None
    if input_threshold is not None:
        if isinstance(input_threshold, int):
            resolved_threshold = "0x" + input_threshold.to_bytes(byteorder="big", signed=False).hex()
        else:
            resolved_threshold = input_threshold
    else:
        resolved_threshold = None

    if (resolved_chain_id := _resolve_chain_id(prefix, params.chainId, constants, out)) is None and (
        params.chainId is not None
    ):
        return None

    return ResolvedTokenAmountParameters(
        token=token_resolved,
        nativeCurrencyAddress=resolved_addresses,
        threshold=resolved_threshold,
        message=constants.resolve_or_none(params.message, out),
        chainId=resolved_chain_id,
        chainIdPath=params.chainIdPath,
    )


def resolve_token_ticker_parameters(
    prefix: DataPath, params: InputTokenTickerParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedTokenTickerParameters | None:
    if (resolved_chain_id := _resolve_chain_id(prefix, params.chainId, constants, out)) is None and (
        params.chainId is not None
    ):
        return None

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


def _resolve_chain_id(
    prefix: DataPath,
    chain_id_input: int | DescriptorPath | InputMapReference | None,
    constants: ConstantProvider,
    out: OutputAdder,
) -> int | ResolvedValueMap | None:
    if chain_id_input is None:
        return None

    if isinstance(chain_id_input, InputMapReference):
        match resolved_map := resolve_map_reference_value(prefix, chain_id_input, ABIDataType.UINT, constants, out):
            case ResolvedValueConstant():
                if not isinstance(resolved_map.value, int):
                    return out.error(
                        title="Invalid chain id",
                        message=f"""Chain id "{resolved_map.value}" from map {chain_id_input.map} is not an integer.""",
                    )
                return resolved_map.value
            case _:
                return resolved_map

    if isinstance(chain_id_input, int):
        return chain_id_input

    # Descriptor path
    resolved_value: Any = constants.resolve(chain_id_input, out)
    if resolved_value is None:
        return None
    if not isinstance(resolved_value, int):
        return out.error(
            title="Invalid chain id",
            message=f"""Chain id "{resolved_value}" from {chain_id_input} is not an integer.""",
        )
    return resolved_value


def resolve_nft_parameters(
    prefix: DataPath, params: InputNftNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedNftNameParameters | None:
    # Resolve collection - can be path, constant, or map reference
    if (
        collection_resolved := resolve_path_constant_or_map_value(
            prefix=prefix,
            input_path=params.collectionPath,
            input_value=params.collection,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
    ) is None:
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
