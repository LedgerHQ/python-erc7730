from typing import Any, assert_never, cast

from erc7730.common.abi import ABIDataType
from erc7730.common.output import OutputAdder
from erc7730.convert.resolved.v2.constants import ConstantProvider
from erc7730.convert.resolved.v2.enums import get_enum, get_enum_id
from erc7730.convert.resolved.v2.values import resolve_path_or_constant_value
from erc7730.model.input.path import ContainerPathStr, DataPathStr, DescriptorPathStr
from erc7730.model.paths.path_ops import data_or_container_path_concat
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
from erc7730.model.paths import ContainerPath, DataPath
from erc7730.model.resolved.display import ResolvedValueConstant, ResolvedValuePath
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
    sender_address: list[Address] | None = None
    if (sender_addr_input := params.senderAddress) is not None:
        # InputMapReference is passed through to resolved model for runtime resolution
        if isinstance(sender_addr_input, InputMapReference):
            # Map references in senderAddress cannot be resolved at conversion time
            out.warning(
                title="Unresolved map reference",
                message="Map reference in senderAddress cannot be resolved at conversion time and will be dropped.",
            )
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
    prefix: DataPath, params: InputInteroperableAddressNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedInteroperableAddressNameParameters | None:
    sender_address: list[Address] | None = None
    if (sender_addr_input := params.senderAddress) is not None:
        # InputMapReference is passed through - similar to address_name
        if isinstance(sender_addr_input, InputMapReference):
            out.warning(
                title="Unresolved map reference",
                message="Map reference in senderAddress cannot be resolved at conversion time and will be dropped.",
            )
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
    prefix: DataPath, params: InputCallDataParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedCallDataParameters | None:
    # Helper to split a ResolvedValue into (path, value) for the calldata model
    def _split_resolved(
        resolved: ResolvedValuePath | ResolvedValueConstant | None,
    ) -> tuple[str | None, Any]:
        if resolved is None:
            return None, None
        if isinstance(resolved, ResolvedValuePath):
            return str(resolved.path), None
        if isinstance(resolved, ResolvedValueConstant):
            return None, resolved.value
        return None, None

    # Resolve callee - can be path, constant, or map reference
    callee_path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = params.calleePath
    callee_value: Address | None = None
    if params.callee is not None and isinstance(params.callee, InputMapReference):
        out.warning(
            title="Unresolved map reference",
            message="Map reference in callee cannot be resolved at conversion time and will be dropped.",
        )
    elif params.callee is not None or params.calleePath is not None:
        resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.calleePath,
            input_value=params.callee,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
        if resolved is None:
            return None
        callee_path, callee_value = _split_resolved(resolved)  # type: ignore[assignment]

    # Resolve selector
    selector_path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = params.selectorPath
    selector_value: str | None = None
    if params.selector is not None and isinstance(params.selector, InputMapReference):
        out.warning(
            title="Unresolved map reference",
            message="Map reference in selector cannot be resolved at conversion time and will be dropped.",
        )
    elif params.selector is not None or params.selectorPath is not None:
        resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.selectorPath,
            input_value=params.selector,
            abi_type=ABIDataType.STRING,
            constants=constants,
            out=out,
        )
        if resolved is not None:
            selector_path, selector_value = _split_resolved(resolved)  # type: ignore[assignment]

    # Resolve amount
    amount_path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = params.amountPath
    amount_value: int | None = None
    if params.amount is not None and isinstance(params.amount, InputMapReference):
        out.warning(
            title="Unresolved map reference",
            message="Map reference in amount cannot be resolved at conversion time and will be dropped.",
        )
    elif params.amount is not None or params.amountPath is not None:
        resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.amountPath,
            input_value=params.amount,
            abi_type=ABIDataType.UINT,
            constants=constants,
            out=out,
        )
        if resolved is not None:
            amount_path, amount_value = _split_resolved(resolved)  # type: ignore[assignment]

    # Resolve spender
    spender_path: DescriptorPathStr | DataPathStr | ContainerPathStr | None = params.spenderPath
    spender_value: Address | None = None
    if params.spender is not None and isinstance(params.spender, InputMapReference):
        out.warning(
            title="Unresolved map reference",
            message="Map reference in spender cannot be resolved at conversion time and will be dropped.",
        )
    elif params.spender is not None or params.spenderPath is not None:
        resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.spenderPath,
            input_value=params.spender,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
        if resolved is not None:
            spender_path, spender_value = _split_resolved(resolved)  # type: ignore[assignment]

    return ResolvedCallDataParameters(
        calleePath=callee_path,
        callee=callee_value,
        selectorPath=selector_path,
        selector=selector_value,
        amountPath=amount_path,
        amount=amount_value,
        spenderPath=spender_path,
        spender=spender_value,
    )


def resolve_token_amount_parameters(
    prefix: DataPath, params: InputTokenAmountParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedTokenAmountParameters | None:
    # Resolve token - can be path, constant, or map reference
    token_value = params.token
    resolved_token: Address | None = None
    if token_value is not None and isinstance(token_value, InputMapReference):
        # Map reference - store as-is for runtime resolution
        # For now, we set to None since resolved model expects Address
        out.warning(
            title="Unresolved map reference",
            message="Map reference in token cannot be resolved at conversion time and will be dropped.",
        )
    else:
        token_resolved = resolve_path_or_constant_value(
            prefix=prefix,
            input_path=params.tokenPath,
            input_value=token_value,
            abi_type=ABIDataType.ADDRESS,
            constants=constants,
            out=out,
        )
        if isinstance(token_resolved, ResolvedValueConstant):
            resolved_token = Address(str(token_resolved.value))

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

    # Resolve chainId - can be int, descriptor path, or map reference
    chain_id_value = params.chainId
    resolved_chain_id: int | None = None
    if chain_id_value is not None and not isinstance(chain_id_value, InputMapReference):
        if isinstance(chain_id_value, int):
            resolved_chain_id = chain_id_value
        else:
            # Descriptor path
            resolved_value: Any = constants.resolve(chain_id_value, out)
            if isinstance(resolved_value, int):
                resolved_chain_id = resolved_value

    return ResolvedTokenAmountParameters(
        tokenPath=params.tokenPath,
        token=resolved_token,
        nativeCurrencyAddress=resolved_addresses,
        threshold=resolved_threshold,
        message=constants.resolve_or_none(params.message, out),
        chainId=resolved_chain_id,
        chainIdPath=params.chainIdPath,
    )


def resolve_token_ticker_parameters(
    prefix: DataPath, params: InputTokenTickerParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedTokenTickerParameters | None:
    # Resolve chainId - can be int, descriptor path, or map reference
    chain_id_value = params.chainId
    resolved_chain_id: int | None = None
    if chain_id_value is not None and not isinstance(chain_id_value, InputMapReference):
        if isinstance(chain_id_value, int):
            resolved_chain_id = chain_id_value
        else:
            # Descriptor path
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
    prefix: DataPath, params: InputNftNameParameters, constants: ConstantProvider, out: OutputAdder
) -> ResolvedNftNameParameters | None:
    # Resolve collection - can be path, constant, or map reference
    collection_value = params.collection
    resolved_collection: Address | None = None
    if collection_value is not None and isinstance(collection_value, InputMapReference):
        # Map reference - needs runtime resolution
        out.warning(
            title="Unresolved map reference",
            message="Map reference in collection cannot be resolved at conversion time and will be dropped.",
        )
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
        if isinstance(collection_resolved, ResolvedValueConstant):
            resolved_collection = Address(str(collection_resolved.value))

    return ResolvedNftNameParameters(
        collectionPath=params.collectionPath,
        collection=resolved_collection,
    )


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
