from typing import assert_never

from erc7730.common.output import OutputAdder
from erc7730.model.input.display import (
    InputAddressNameParameters,
    InputCallDataParameters,
    InputDateParameters,
    InputEnumParameters,
    InputFieldParameters,
    InputNftNameParameters,
    InputTokenAmountParameters,
    InputUnitParameters,
)
from erc7730.model.paths import DescriptorPath
from erc7730.model.paths.path_ops import to_absolute
from erc7730.model.resolved.display import (
    ResolvedAddressNameParameters,
    ResolvedCallDataParameters,
    ResolvedDateParameters,
    ResolvedEnumParameters,
    ResolvedFieldParameters,
    ResolvedNftNameParameters,
    ResolvedTokenAmountParameters,
    ResolvedUnitParameters,
)


def convert_field_parameters(params: InputFieldParameters, out: OutputAdder) -> ResolvedFieldParameters | None:
    match params:
        case None:
            return None
        case InputAddressNameParameters():
            return convert_address_name_parameters(params, out)
        case InputCallDataParameters():
            return convert_calldata_parameters(params, out)
        case InputTokenAmountParameters():
            return convert_token_amount_parameters(params, out)
        case InputNftNameParameters():
            return convert_nft_parameters(params, out)
        case InputDateParameters():
            return convert_date_parameters(params, out)
        case InputUnitParameters():
            return convert_unit_parameters(params, out)
        case InputEnumParameters():
            return convert_enum_parameters(params, out)
        case _:
            assert_never(params)


def convert_address_name_parameters(
    params: InputAddressNameParameters, out: OutputAdder
) -> ResolvedAddressNameParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if isinstance(params.types, DescriptorPath) or isinstance(params.sources, DescriptorPath):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedAddressNameParameters(types=params.types, sources=params.sources)


def convert_calldata_parameters(params: InputCallDataParameters, out: OutputAdder) -> ResolvedCallDataParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if isinstance(params.selector, DescriptorPath) or isinstance(params.calleePath, DescriptorPath):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedCallDataParameters(
        selector=params.selector,
        calleePath=to_absolute(params.calleePath),
    )


def convert_token_amount_parameters(
    params: InputTokenAmountParameters, out: OutputAdder
) -> ResolvedTokenAmountParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if (
        isinstance(params.tokenPath, DescriptorPath)
        or isinstance(params.nativeCurrencyAddress, DescriptorPath)
        or isinstance(params.threshold, DescriptorPath)
        or isinstance(params.message, DescriptorPath)
    ):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedTokenAmountParameters(
        tokenPath=None if params.tokenPath is None else to_absolute(params.tokenPath),
        nativeCurrencyAddress=params.nativeCurrencyAddress,
        threshold=params.threshold,
        message=params.message,
    )


def convert_nft_parameters(params: InputNftNameParameters, out: OutputAdder) -> ResolvedNftNameParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if isinstance(params.collectionPath, DescriptorPath):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedNftNameParameters(collectionPath=to_absolute(params.collectionPath))


def convert_date_parameters(params: InputDateParameters, out: OutputAdder) -> ResolvedDateParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if isinstance(params.encoding, DescriptorPath):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedDateParameters(encoding=params.encoding)


def convert_unit_parameters(params: InputUnitParameters, out: OutputAdder) -> ResolvedUnitParameters | None:
    # TODO: resolution of descriptor paths not implemented
    if (isinstance(params.base, DescriptorPath) or isinstance(params.decimals, DescriptorPath)) or isinstance(
        params.prefix, DescriptorPath
    ):
        raise NotImplementedError("Resolution of descriptor paths not implemented")
    return ResolvedUnitParameters(
        base=params.base,
        decimals=params.decimals,
        prefix=params.prefix,
    )


def convert_enum_parameters(params: InputEnumParameters, out: OutputAdder) -> ResolvedEnumParameters | None:
    return ResolvedEnumParameters.model_validate({"$ref": params.ref})  # TODO must inline here
